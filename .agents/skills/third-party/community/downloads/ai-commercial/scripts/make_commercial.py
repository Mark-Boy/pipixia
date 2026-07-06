#!/usr/bin/env python3
"""
ai-commercial orchestrator.

Reads $PROJECT_DIR/brief/brief.json, dispatches each scene by type, generates VO,
composes the final commercial in the requested aspect ratios.

Scene types:
  runway_atmosphere  — Runway t2v
  runway_i2v         — Runway i2v with a seed image
  screenshot_kenburns — Ken Burns motion on a still image (ffmpeg)
  logo_reveal        — ffmpeg logo scale-up animation
  cta_slide          — designed CTA card with logo + URL + headline (ffmpeg + PIL)
  testimonial        — quote + name + photo card
  bumper             — branded interstitial
  screen_recording   — pre-recorded screen capture

Usage:
  export PROJECT_DIR=~/clientname-commercial
  python3 make_commercial.py
  python3 make_commercial.py --only hook problem    # regenerate specific scenes
  python3 make_commercial.py --aspect 16:9          # render only one aspect
"""
import argparse, json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(os.environ.get("PROJECT_DIR", os.getcwd())).expanduser().resolve()
BRIEF_PATH = ROOT / "brief/brief.json"
ASSETS = ROOT / "assets"
GEN = ROOT / "generated"
SCENES_DIR = GEN / "scenes"
RUNWAY_DIR = GEN / "runway"
VO_DIR = GEN / "vo"
MUSIC_DIR = GEN / "music"
OVERLAYS_DIR = GEN / "overlays"
OUTPUT = ROOT / "output"

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent

# Aspect ratios → output dimensions (1080p baseline)
ASPECT_DIMS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1":  (1080, 1080),
    "4:5":  (1080, 1350),
    "21:9": (2560, 1080),
}


def run(*args, check=True, **kwargs):
    return subprocess.run(args, check=check, **kwargs)


def ensure_dirs():
    for d in (GEN, SCENES_DIR, RUNWAY_DIR, VO_DIR, MUSIC_DIR, OVERLAYS_DIR, OUTPUT):
        d.mkdir(parents=True, exist_ok=True)


def load_brief() -> dict:
    if not BRIEF_PATH.exists():
        sys.exit(f"missing brief: {BRIEF_PATH}\n\nCopy a template:\n"
                 f"  cp ~/.claude/skills/ai-commercial/templates/saas-demo.json "
                 f"{BRIEF_PATH}")
    return json.loads(BRIEF_PATH.read_text())


# ---------- VO synthesis (ElevenLabs direct) ----------

def synth_vo(text: str, voice_cfg: dict, dest: pathlib.Path):
    """Synthesize VO via ElevenLabs API. Returns the audio file path."""
    if dest.exists():
        return dest
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("ELEVENLABS_API_KEY missing in env (~/.zshrc)")
    voice_id = voice_cfg.get("voice_id") or os.environ.get("ELEVENLABS_VOICE_ID")
    if not voice_id:
        sys.exit("voice_id missing in brief AND ELEVENLABS_VOICE_ID env unset")

    import json as _json
    from urllib.request import Request, urlopen
    body = _json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": voice_cfg.get("stability", 0.5),
            "similarity_boost": voice_cfg.get("similarity_boost", 0.75),
        },
    }).encode()
    req = Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=body,
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    with urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"  VO: {dest.name} ({len(text)} chars)")
    return dest


# ---------- Scene dispatchers ----------

def dispatch_runway_atmosphere(scene: dict, brief: dict) -> pathlib.Path:
    """Generate a Runway t2v clip."""
    sid = scene["id"]
    out = RUNWAY_DIR / f"{sid}.mp4"
    if out.exists():
        return out
    # Reuse intro-trailer's generate.py pattern — direct API call
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    import json as _json, time
    api_key = _read_runway_key()
    duration = scene["duration"]
    # Runway constraints — round to allowed values
    duration = _round_runway_duration(scene.get("model", "veo3.1"), duration)
    body = {
        "model": scene.get("model", "veo3.1"),
        "ratio": "1280:720",
        "duration": int(duration) if duration == int(duration) else duration,
        "promptText": scene["prompt"],
    }
    print(f"  Runway t2v: submit  model={body['model']} dur={body['duration']}s")
    task_id = _runway_submit("text_to_video", body, api_key)
    info = _runway_poll(task_id, api_key)
    if info["status"] != "SUCCEEDED":
        sys.exit(f"  Runway failed: {info.get('failure')}")
    _download(info["output"][0], out)
    return out


def dispatch_runway_i2v(scene: dict, brief: dict) -> pathlib.Path:
    """Generate a Runway image-to-video clip."""
    sid = scene["id"]
    out = RUNWAY_DIR / f"{sid}.mp4"
    if out.exists():
        return out
    import base64, json as _json, mimetypes
    api_key = _read_runway_key()
    seed = ROOT / scene["seedImage"]
    if not seed.exists():
        sys.exit(f"  Missing seed image: {seed}")
    mime = mimetypes.guess_type(str(seed))[0] or "image/jpeg"
    data_uri = f"data:{mime};base64,{base64.b64encode(seed.read_bytes()).decode()}"
    duration = _round_runway_duration(scene.get("model", "gen4_turbo"), scene["duration"])
    body = {
        "model": scene.get("model", "gen4_turbo"),
        "ratio": "1280:720",
        "duration": int(duration) if duration == int(duration) else duration,
        "promptText": scene["prompt"],
        "promptImage": data_uri,
    }
    print(f"  Runway i2v: submit  model={body['model']} dur={body['duration']}s")
    task_id = _runway_submit("image_to_video", body, api_key)
    info = _runway_poll(task_id, api_key)
    if info["status"] != "SUCCEEDED":
        sys.exit(f"  Runway failed: {info.get('failure')}")
    _download(info["output"][0], out)
    return out


def dispatch_screenshot_kenburns(scene: dict, brief: dict) -> pathlib.Path:
    """Apply Ken Burns motion to a still image."""
    sid = scene["id"]
    out = SCENES_DIR / f"{sid}-kb.mp4"
    src = ROOT / scene["image"]
    if not src.exists():
        sys.exit(f"  Missing image: {src}")
    dur = scene["duration"]
    fps = 24
    frames = int(dur * fps)
    motion = scene.get("motion", "zoom_in")
    if motion == "zoom_in":
        z = f"min(zoom+{0.12/frames:.5f},1.12)"
    elif motion == "zoom_out":
        z = f"max(zoom-{0.12/frames:.5f},1.0)"
    elif motion == "pan_right":
        z = "1.10"
    elif motion == "pan_left":
        z = "1.10"
    else:  # drift
        z = "1.05"
    vf = (
        f"scale=2880:1620:force_original_aspect_ratio=increase,crop=2880:1620,"
        f"zoompan=z='{z}':d={frames}:s=1920x1080:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={fps}"
    )
    run("ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(src),
        "-t", str(dur), "-r", str(fps),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(out))
    return out


def dispatch_logo_reveal(scene: dict, brief: dict) -> pathlib.Path:
    """ffmpeg logo scale-up animation."""
    sid = scene["id"]
    out = SCENES_DIR / f"{sid}-logo.mp4"
    logo = ROOT / brief["brand"]["logo"]
    if not logo.exists():
        sys.exit(f"  Missing logo: {logo}")
    dur = scene["duration"]
    # Logo aspect: compute from image dims
    # Just default to 1717x1080 for square-ish logos; fit to 1080 height
    vf = (
        f"color=c=black:s=1920x1080:r=24,format=yuva420p"
    )
    # Two-input approach: black bg + animated logo overlay
    run("ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s=1920x1080:r=24:d={dur}",
        "-loop", "1", "-i", str(logo),
        "-filter_complex",
        f"[1:v]format=rgba,scale=w='1717*(0.05+0.95*t/{dur})':h='1080*(0.05+0.95*t/{dur})':eval=frame[lg];"
        f"[0:v][lg]overlay=x='(W-w)/2':y='(H-h)/2'[v]",
        "-map", "[v]", "-t", str(dur),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(out))
    return out


def dispatch_cta_slide(scene: dict, brief: dict) -> pathlib.Path:
    """Designed CTA card with logo + URL + headline."""
    sid = scene["id"]
    out = SCENES_DIR / f"{sid}-cta.mp4"
    dur = scene["duration"]
    brand = brief["brand"]
    headline = scene.get("headline", brand.get("tagline", ""))
    subhead = scene.get("subhead", "")
    primary = brand.get("primaryColor", "#0f172a")
    accent = brand.get("accentColor", "#3b82f6")
    # Render a PNG via ImageMagick, then loop into a video
    overlay_png = OVERLAYS_DIR / f"{sid}-cta.png"
    fonts = {
        "h1": "/System/Library/Fonts/Supplemental/Impact.ttf",
        "body": "/System/Library/Fonts/HelveticaNeue.ttc",
    }
    # Build PNG with ImageMagick
    cmd = ["magick", "-size", "1920x1080", f"gradient:{primary}-{primary}cc"]
    if brand.get("logo"):
        cmd += ["-gravity", "north", "(", str(ROOT / brand["logo"]), "-resize", "x180", ")", "-geometry", "+0+100", "-composite"]
    cmd += [
        "-font", fonts["h1"], "-pointsize", "84", "-fill", "white", "-gravity", "center",
        "-annotate", "+0-20", headline.replace("\n", "  "),
    ]
    if subhead:
        cmd += ["-font", fonts["body"], "-pointsize", "40", "-fill", accent,
                "-gravity", "center", "-annotate", f"+0+80", subhead.split("\n")[0]]
        if "\n" in subhead:
            cmd += ["-fill", "white", "-gravity", "center",
                    "-annotate", f"+0+140", subhead.split("\n", 1)[1]]
    cmd += [str(overlay_png)]
    run(*cmd)
    # Loop the PNG into a video of the right duration
    run("ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(overlay_png),
        "-t", str(dur), "-r", "24",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(out))
    return out


def dispatch_testimonial(scene: dict, brief: dict) -> pathlib.Path:
    """Quote + name + photo card."""
    sid = scene["id"]
    out = SCENES_DIR / f"{sid}-testimonial.mp4"
    dur = scene["duration"]
    quote = scene.get("quote", "")
    name = scene.get("name", "")
    photo = ROOT / scene["photo"] if scene.get("photo") else None
    overlay_png = OVERLAYS_DIR / f"{sid}-testimonial.png"
    primary = brief["brand"].get("primaryColor", "#0f172a")
    fonts = {
        "quote": "/System/Library/Fonts/Supplemental/Futura.ttc",
        "name": "/System/Library/Fonts/HelveticaNeue.ttc",
    }
    cmd = ["magick", "-size", "1920x1080", f"gradient:{primary}-#000000"]
    if photo and photo.exists():
        cmd += ["(", str(photo), "-resize", "320x320^", "-gravity", "center",
                "-extent", "320x320", "(", "+clone", "-alpha", "extract",
                "-draw", "fill black polygon 0,0 0,320 320,0 fill white circle 160,160 160,1",
                "-flatten", ")", "-alpha", "off", "-compose", "CopyOpacity", "-composite",
                ")", "-gravity", "west", "-geometry", "+200+0", "-composite"]
    cmd += [
        "-font", fonts["quote"], "-pointsize", "56", "-fill", "white",
        "-gravity", "east", "-annotate", "+200+0", f'"{quote}"',
        "-font", fonts["name"], "-pointsize", "32", "-fill", "#aaaaaa",
        "-gravity", "east", "-annotate", "+200+120", f"— {name}",
        str(overlay_png),
    ]
    try:
        run(*cmd)
    except subprocess.CalledProcessError:
        # Fallback: simpler card without circular photo
        run("magick", "-size", "1920x1080", f"gradient:{primary}-#000000",
            "-font", fonts["quote"], "-pointsize", "56", "-fill", "white",
            "-gravity", "center", "-annotate", "+0-40", f'"{quote}"',
            "-font", fonts["name"], "-pointsize", "32", "-fill", "#aaaaaa",
            "-gravity", "center", "-annotate", "+0+60", f"— {name}",
            str(overlay_png))
    run("ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(overlay_png),
        "-t", str(dur), "-r", "24",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(out))
    return out


# ---------- Runway API helpers ----------

def _read_runway_key():
    p = pathlib.Path.home() / ".runway/credentials"
    if not p.exists():
        sys.exit("missing ~/.runway/credentials")
    for line in p.read_text().splitlines():
        if line.startswith("RUNWAY_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("RUNWAY_API_KEY not in credentials file")


def _runway_submit(endpoint: str, body: dict, key: str) -> str:
    import json as _json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    req = Request(
        f"https://api.dev.runwayml.com/v1/{endpoint}",
        data=_json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json",
        },
    )
    try:
        return _json.loads(urlopen(req, timeout=60).read())["id"]
    except HTTPError as e:
        sys.exit(f"Runway HTTP {e.code}: {e.read().decode()}")


def _runway_poll(task_id: str, key: str) -> dict:
    import json as _json, time
    from urllib.request import Request, urlopen
    delay = 5
    while True:
        req = Request(
            f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
            headers={
                "Authorization": f"Bearer {key}",
                "X-Runway-Version": "2024-11-06",
            },
        )
        info = _json.loads(urlopen(req, timeout=30).read())
        if info["status"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return info
        print(f"    ... {info['status']} (sleep {delay}s)")
        time.sleep(delay)
        delay = min(delay + 5, 30)


def _download(url: str, dest: pathlib.Path):
    from urllib.request import urlopen
    with urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())


def _round_runway_duration(model: str, requested: float) -> float:
    """Map a desired duration to the model's allowed enum."""
    allowed = {
        "gen3a_turbo": [5, 10],
        "gen4_turbo": [5, 10],
        "gen4.5": [5],
        "veo3": [8],
        "veo3.1": [8],
        "veo3.1_fast": [4, 6, 8],
    }.get(model, [5, 10])
    return min(allowed, key=lambda x: abs(x - requested))


# ---------- Per-scene composition (VO + visual + music duck) ----------

def compose_scene(scene: dict, visual_path: pathlib.Path, brief: dict) -> pathlib.Path:
    """Compose final per-scene clip: visual + (optional VO) + trimmed to scene duration."""
    sid = scene["id"]
    out = SCENES_DIR / f"{sid}-final.mp4"
    dur = scene["duration"]

    if scene.get("vo"):
        vo_path = synth_vo(scene["vo"], brief["voice"], VO_DIR / f"{sid}.mp3")
        run("ffmpeg", "-y", "-loglevel", "error",
            "-i", str(visual_path), "-i", str(vo_path),
            "-t", str(dur), "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            str(out))
    else:
        # No VO — silent track
        run("ffmpeg", "-y", "-loglevel", "error",
            "-i", str(visual_path), "-t", str(dur),
            "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            str(out))
    return out


# ---------- Main pipeline ----------

DISPATCHERS = {
    "runway_atmosphere": dispatch_runway_atmosphere,
    "runway_i2v":        dispatch_runway_i2v,
    "screenshot_kenburns": dispatch_screenshot_kenburns,
    "logo_reveal":       dispatch_logo_reveal,
    "cta_slide":         dispatch_cta_slide,
    "testimonial":       dispatch_testimonial,
}


def render_aspect(scene_clips: list, brief: dict, aspect: str):
    """Concat scene clips with crossfades and render to a specific aspect ratio."""
    w, h = ASPECT_DIMS[aspect]
    label = aspect.replace(":", "x")
    out = OUTPUT / f"commercial-{label}.mp4"

    # Build concat list
    concat_list = OUTPUT / f"_concat-{label}.txt"
    with open(concat_list, "w") as f:
        for c in scene_clips:
            f.write(f"file '{c}'\n")

    # First concat then re-scale+crop to target aspect
    intermediate = OUTPUT / f"_intermediate-{label}.mp4"
    run("ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", str(intermediate))

    # Mix music underneath if configured
    music_style = brief.get("music", {}).get("style")
    music_vol = brief.get("music", {}).get("volume", 0.25)
    if music_style and music_style != "none":
        music_bed = MUSIC_DIR / "bed.mp3"
        if not music_bed.exists():
            # Auto-generate via social-video's procedural music synthesizer
            print(f"  Music bed not at {music_bed} — auto-generating ({music_style})...")
            total_dur = sum(s["duration"] for s in brief["scenes"]) + 4  # +4s tail for safety
            gen_script = SCRIPTS_DIR / "generate_music.py"
            try:
                subprocess.run([
                    sys.executable, str(gen_script),
                    "--style", music_style,
                    "--duration", str(total_dur),
                    "--out", str(music_bed),
                ], check=True)
            except subprocess.CalledProcessError as e:
                print(f"  ! Music gen failed: {e} — proceeding without music")
        if music_bed.exists():
            run("ffmpeg", "-y", "-loglevel", "error",
                "-i", str(intermediate), "-i", str(music_bed),
                "-filter_complex",
                f"[1:a]volume={music_vol},aloop=loop=-1:size=2e+09[m];"
                f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                str(out))
            intermediate.unlink()
            concat_list.unlink()
            return out

    intermediate.replace(out)
    concat_list.unlink()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None, help="re-render specific scene ids")
    ap.add_argument("--aspect", nargs="*", default=None, help="render only specific aspect ratios")
    args = ap.parse_args()

    ensure_dirs()
    brief = load_brief()

    print(f"Project: {brief.get('type')} ({brief.get('duration')}s)")
    print(f"Brand:   {brief['brand']['name']}")
    print()

    scene_finals = []
    for scene in brief["scenes"]:
        sid = scene["id"]
        if args.only and sid not in args.only:
            # still need a previously-finalized clip
            existing = SCENES_DIR / f"{sid}-final.mp4"
            if existing.exists():
                scene_finals.append(existing)
                continue
            else:
                print(f"[{sid}] skip — not in --only and no previous render")
                continue

        print(f"[{sid}] {scene['type']:22s} ({scene['duration']}s)")
        dispatcher = DISPATCHERS.get(scene["type"])
        if not dispatcher:
            sys.exit(f"  unknown scene type: {scene['type']}")

        visual = dispatcher(scene, brief)
        final = compose_scene(scene, visual, brief)
        scene_finals.append(final)

    print()
    aspects = args.aspect or brief.get("aspectRatios", ["16:9"])
    for asp in aspects:
        if asp not in ASPECT_DIMS:
            print(f"  unknown aspect: {asp} — skipping")
            continue
        print(f"Rendering {asp}...")
        out = render_aspect(scene_finals, brief, asp)
        print(f"  → {out}")

    print("\nDone.")
    if aspects:
        first = OUTPUT / f"commercial-{aspects[0].replace(':', 'x')}.mp4"
        if first.exists():
            subprocess.run(["open", str(first)])


if __name__ == "__main__":
    main()
