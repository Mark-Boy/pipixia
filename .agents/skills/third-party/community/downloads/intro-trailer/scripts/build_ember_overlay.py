#!/usr/bin/env python3
"""
Generate the persistent ember/smoke overlay layer via Runway veo3.1 t2v.
This is the single biggest unifier in the seamless composite — drifts under every shot.

Output: $PROJECT_DIR/overlays-source/embers-veo31-8s.mp4

Cost: ~75 credits (one-time per project).
"""
import json, os, pathlib, sys, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API_BASE = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"
ROOT = pathlib.Path(os.environ.get("PROJECT_DIR", os.getcwd())).expanduser().resolve()
DEST = ROOT / "overlays-source/embers-veo31-8s.mp4"

p = pathlib.Path.home() / ".runway/credentials"
if not p.exists():
    sys.exit("missing ~/.runway/credentials")
key = next(l for l in p.read_text().splitlines() if l.startswith("RUNWAY_API_KEY=")).split("=", 1)[1].strip()


def http(method, url, body=None):
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {key}",
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
    })
    try:
        return json.loads(urlopen(req, timeout=60).read())
    except HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()}")


def main():
    if DEST.exists():
        print(f"Ember overlay already exists at {DEST} — skipping.")
        return

    body = {
        "model": "veo3.1",
        "ratio": "1280:720",
        "duration": 8,
        "promptText": (
            "Slow drifting glowing orange, gold, and amber embers floating upward and gently "
            "sideways across the entire frame. Thin tendrils of dark smoke wisping and curling "
            "slowly. Pure jet-black background, no other elements, no figures, no text, no logos. "
            "Volumetric particle effect, atmospheric, dreamy slow motion, deep contrast between "
            "the bright glowing embers and the pitch black space."
        ),
    }
    print("Submitting ember overlay job...")
    resp = http("POST", f"{API_BASE}/text_to_video", body)
    task_id = resp["id"]
    print(f"task_id={task_id}")

    delay = 5
    while True:
        info = http("GET", f"{API_BASE}/tasks/{task_id}")
        status = info.get("status")
        if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        print(f"  ... {status} (sleep {delay}s)")
        time.sleep(delay)
        delay = min(delay + 5, 30)

    if status != "SUCCEEDED":
        sys.exit(f"FAILED: {info.get('failure')}")

    out_url = info["output"][0]
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(out_url, timeout=120) as r, open(DEST, "wb") as f:
        f.write(r.read())
    print(f"\nSaved: {DEST}")


if __name__ == "__main__":
    main()
