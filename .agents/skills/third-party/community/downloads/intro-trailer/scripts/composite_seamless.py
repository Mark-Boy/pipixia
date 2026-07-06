#!/usr/bin/env python3
"""
303 intro compositor v3 — SEAMLESS pass.

Unifies 18 Runway-generated clips into one continuous cinematic intro by applying:
  1. Cinematic color grade to every clip (crushed blacks, warm shadows, red highlights)
  2. Persistent ember/smoke overlay layer running underneath every shot at ~12% opacity
  3. Subtle radial vignette at the edges
  4. Light film grain via ffmpeg noise filter
  5. Variable crossfade durations per junction (long blends on atmosphere, tight on members,
     hard cuts at logo BANG moments)
  6. Lower-third + URL card composited on top after grading

Inputs:
  ~/303band-intro/clips/*.mp4              (raw Runway outputs)
  ~/303band-intro/overlays-source/embers-veo31-8s.mp4  (ember layer)
  ~/303band-intro/output/overlays/vignette.png
  ~/303band-intro/output/overlays/lt_{06..11}.png
  ~/303band-intro/output/overlays/url_card.png
  ~/303band-intro/scripts/prompts.json

Output: ~/303band-intro/output/303-intro-1080p.mp4
"""
import json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(os.environ.get("PROJECT_DIR", os.getcwd()))
CLIPS = ROOT / "clips"
OVERLAYS = ROOT / "output/overlays"
EMBER_SRC = ROOT / "overlays-source/embers-veo31-8s.mp4"
OUT_DIR = ROOT / "output"
TMP = OUT_DIR / "tmp"
PROMPTS = ROOT / "scripts/prompts.json"

# ------------- color grade applied to every clip -------------
# Crush blacks slightly, lift highlights, warm shadows (more red, less blue),
# bump contrast and saturation slightly. Tuned for the heaven/hell/fire palette.
GRADE = (
    "eq=contrast=1.12:saturation=1.08:brightness=-0.01,"
    "colorbalance=rs=0.08:gs=-0.02:bs=-0.08:rm=0.04:gm=-0.01:bm=-0.04,"
    "curves=master='0/0 0.08/0.04 0.92/0.96 1/1',"
    "noise=alls=4:allf=t"  # subtle temporal film grain on luma
)

# ------------- per-junction crossfade durations (seconds) -------------
# Order follows prompts.json shot order. v4 chain:
# 01→02→03→04→04b→05→05b→06→06c→07→07c→08→08c→09→09c→10→10c→11→11c→12→12b→13→14→15
XFADE = {
    ("01", "02"):  0.8,
    ("02", "03"):  0.7,
    ("03", "04"):  0.6,
    ("04", "04b"): 0.2,   # collision white flash, near-hard
    ("04b","05"):  0.4,   # lightning+fire → logo scale-up (smooth)
    ("05", "05b"): 0.1,   # scale-up full → BANG explosion (hard cut)
    ("05b","06"):  0.6,
    ("06", "06c"): 0.3,   # member → cartoon flash
    ("06c","07"):  0.3,
    ("07", "07c"): 0.3,
    ("07c","08"): 0.3,
    ("08", "08c"): 0.3,
    ("08c","09"): 0.3,
    ("09", "09c"): 0.3,
    ("09c","10"): 0.3,
    ("10", "10c"): 0.3,
    ("10c","11"): 0.3,
    ("11", "11c"): 0.3,
    ("11c","12"): 0.5,
    ("12", "12b"): 0.6,   # collage → Cops for Cancer
    ("12b","13"): 0.6,
    ("13", "14"): 0.5,
    ("14", "15"): 0.6,
}

EMBER_OPACITY = 0.12   # how much the ember layer shows through
VIGNETTE_OPACITY = 1.0  # the PNG already has alpha baked in; use as-is


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    cfg = json.loads(PROMPTS.read_text())
    shots = cfg["shots"]
    TMP.mkdir(parents=True, exist_ok=True)

    vignette = OVERLAYS / "vignette.png"
    if not vignette.exists():
        sys.exit("vignette PNG missing; run render_overlays.sh first")
    has_ember = EMBER_SRC.exists()
    if not has_ember:
        print(f"NOTE: ember overlay not found at {EMBER_SRC} — proceeding without ember layer.")

    # 1) Per-clip: scale → grade → ember-tile → vignette
    print("Grading + overlaying each clip...")
    for s in shots:
        src = CLIPS / f"{s['id']}.mp4"
        if not src.exists():
            sys.exit(f"missing clip: {src}")
        dst = TMP / f"n_{s['id']}.mp4"

        # Build filter graph for this clip
        # [0:v] = source clip, [1:v] = ember loop (if present), [2:v] = vignette PNG
        if has_ember:
            filters = (
                f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=24,"
                f"{GRADE},format=yuva420p[base];"
                f"[1:v]scale=1920:1080,setsar=1,fps=24,format=rgba,"
                f"colorchannelmixer=aa={EMBER_OPACITY}[em];"
                f"[base][em]overlay=0:0:shortest=1[base2];"
                f"[2:v]scale=1920:1080,format=rgba[vig];"
                f"[base2][vig]overlay=0:0[v]"
            )
            inputs = [
                "-i", str(src),
                "-stream_loop", "-1", "-i", str(EMBER_SRC),
                "-loop", "1", "-i", str(vignette),
            ]
        else:
            filters = (
                f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=24,"
                f"{GRADE},format=yuva420p[base];"
                f"[1:v]scale=1920:1080,format=rgba[vig];"
                f"[base][vig]overlay=0:0[v]"
            )
            inputs = [
                "-i", str(src),
                "-loop", "1", "-i", str(vignette),
            ]

        run("ffmpeg", "-y", "-loglevel", "error", *inputs,
            "-filter_complex", filters,
            "-map", "[v]",
            "-t", str(s["duration"]),  # truncate to clip's intended duration
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(dst))

    # 2) Composite lower-thirds on member shots (after grading so they sit crisp)
    print("Compositing member lower-thirds...")
    for s in shots:
        lt = s.get("lowerThird")
        if not lt:
            continue
        clip = TMP / f"n_{s['id']}.mp4"
        overlay = OVERLAYS / f"lt_{s['id']}.png"
        if not overlay.exists():
            continue
        out = TMP / f"lt_{s['id']}.mp4"
        run("ffmpeg", "-y", "-loglevel", "error",
            "-i", str(clip), "-loop", "1", "-i", str(overlay),
            "-filter_complex",
            "[1:v]format=rgba,fade=in:st=0.3:d=0.4:alpha=1[lt];"
            "[0:v][lt]overlay=0:0:shortest=1[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(out))
        out.replace(clip)

    # 3) Composite tagline card (KICK ASS ROCK AND ROLL 2026 + URL) on final shot
    print("Compositing tagline card...")
    final_id = shots[-1]["id"]
    clip = TMP / f"n_{final_id}.mp4"
    url_card = OVERLAYS / "tagline_card.png"
    if not url_card.exists():
        url_card = OVERLAYS / "url_card.png"  # fallback
    if url_card.exists():
        out = TMP / f"url_{final_id}.mp4"
        run("ffmpeg", "-y", "-loglevel", "error",
            "-i", str(clip), "-loop", "1", "-i", str(url_card),
            "-filter_complex",
            "[1:v]format=rgba,fade=in:st=1.0:d=0.5:alpha=1[uc];"
            "[0:v][uc]overlay=0:0:shortest=1[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(out))
        out.replace(clip)

    # 4) Chain with variable xfade durations
    print("Chaining with variable xfade durations...")
    inputs = []
    for s in shots:
        inputs += ["-i", str(TMP / f"n_{s['id']}.mp4")]

    chain = []
    cum_offset = 0.0
    prev_label = "[0:v]"
    for i in range(1, len(shots)):
        prev_id = shots[i-1]["id"]
        cur_id = shots[i]["id"]
        prev_dur = float(shots[i-1]["duration"])
        xf = XFADE.get((prev_id, cur_id), 0.5)
        if i == 1:
            cum_offset = prev_dur - xf
        else:
            cum_offset += prev_dur - xf
        out_label = f"[v{i}]"
        chain.append(
            f"{prev_label}[{i}:v]xfade=transition=fade:duration={xf}:"
            f"offset={cum_offset:.3f}{out_label}"
        )
        prev_label = out_label

    filter_complex = ";".join(chain)
    final_label = prev_label

    final_mp4 = OUT_DIR / "303-intro-1080p.mp4"
    run("ffmpeg", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", final_label,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(final_mp4))

    # 5) ProRes archive
    final_mov = OUT_DIR / "303-intro-1080p-prores.mov"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final_mp4),
                    "-c:v", "prores_ks", "-profile:v", "3", "-an", str(final_mov)],
                   check=False)

    print(f"\nDone.")
    print(f"  H.264:  {final_mp4}")
    print(f"  ProRes: {final_mov}")
    subprocess.run(["open", str(final_mp4)])


if __name__ == "__main__":
    main()
