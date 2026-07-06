#!/usr/bin/env python3
"""
303 intro generator — submits prompts.json shots to Runway, polls, downloads MP4s.

Usage:
    python3 generate.py                 # generate every shot not yet downloaded
    python3 generate.py --only 05 07    # regenerate specific shot ids (overwrites)
    python3 generate.py --dry-run       # show what would be submitted, do not call API
"""
import argparse, base64, json, mimetypes, os, pathlib, sys, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = pathlib.Path(os.environ.get("PROJECT_DIR", os.getcwd())).expanduser().resolve()
CLIPS = ROOT / "clips"
PROMPTS = ROOT / "scripts" / "prompts.json"
API_BASE = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"


def load_key() -> str:
    p = pathlib.Path.home() / ".runway" / "credentials"
    if not p.exists():
        sys.exit("missing ~/.runway/credentials")
    for line in p.read_text().splitlines():
        if line.startswith("RUNWAY_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("RUNWAY_API_KEY not found in credentials file")


def encode_image(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def http_json(method: str, url: str, key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {key}",
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
    })
    try:
        with urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {url}\n{body}")


def submit(shot: dict, key: str) -> str:
    submit_dur = shot.get("runwayDuration", shot["duration"])
    common = {
        "model": shot["model"],
        "ratio": shot["ratio"],
        "duration": int(submit_dur) if submit_dur == int(submit_dur) else submit_dur,
        "promptText": shot["promptText"],
    }
    if shot["mode"] == "image_to_video":
        seed_path = ROOT / shot["seedImage"]
        if not seed_path.exists():
            raise SystemExit(f"seed image missing: {seed_path}")
        common["promptImage"] = encode_image(seed_path)
        endpoint = "/image_to_video"
    elif shot["mode"] == "text_to_video":
        endpoint = "/text_to_video"
    else:
        raise SystemExit(f"unknown mode: {shot['mode']}")
    resp = http_json("POST", API_BASE + endpoint, key, common)
    return resp["id"]


def poll(task_id: str, key: str) -> dict:
    delay = 5
    while True:
        info = http_json("GET", f"{API_BASE}/tasks/{task_id}", key)
        status = info.get("status")
        if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return info
        print(f"  ... {status} (sleep {delay}s)")
        time.sleep(delay)
        delay = min(delay + 5, 30)


def download(url: str, dest: pathlib.Path):
    with urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(PROMPTS.read_text())
    CLIPS.mkdir(exist_ok=True)

    if args.dry_run:
        for s in cfg["shots"]:
            seed = s.get("seedImage", "—")
            print(f"[{s['id']}] {s['mode']:14s} {s['model']:14s} {s['duration']}s  seed={seed}")
            print(f"        {s['promptText'][:100]}...")
        return

    key = load_key()
    selected = cfg["shots"] if not args.only else [s for s in cfg["shots"] if s["id"] in args.only]

    failures = []
    for s in selected:
        out = CLIPS / f"{s['id']}.mp4"
        if out.exists() and not args.only:
            print(f"[{s['id']}] skip (already downloaded)")
            continue
        if s["mode"] not in ("image_to_video", "text_to_video"):
            print(f"[{s['id']}] skip (mode={s['mode']} — not a Runway video job)")
            continue
        # If seed image is missing (e.g. cartoons not generated yet), skip
        if s["mode"] == "image_to_video":
            seed = ROOT / s["seedImage"]
            if not seed.exists():
                print(f"[{s['id']}] skip (seed not ready: {s['seedImage']})")
                continue
        print(f"[{s['id']}] submit  model={s['model']} mode={s['mode']} dur={s['duration']}s")
        try:
            task_id = submit(s, key)
            print(f"[{s['id']}] task_id={task_id}")
            result = poll(task_id, key)
            if result["status"] != "SUCCEEDED":
                print(f"[{s['id']}] FAILED: {result.get('failure', {})}")
                failures.append(s['id'])
                continue
            outputs = result.get("output", [])
            if not outputs:
                print(f"[{s['id']}] no output URLs in response")
                failures.append(s['id'])
                continue
            download(outputs[0], out)
            print(f"[{s['id']}] saved -> {out}")
        except Exception as e:
            print(f"[{s['id']}] ERROR: {e}")
            failures.append(s['id'])
    if failures:
        print(f"\nFailures: {failures}")
    else:
        print("\nAll shots succeeded.")


if __name__ == "__main__":
    main()
