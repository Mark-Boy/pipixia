#!/usr/bin/env python3
"""
Generate 6 cartoon heaven/hell portraits via Runway image gen.
Each uses the real member photo as reference + prompt for cartoon style.

Output: ~/303band-intro/cartoons/{id}.png
"""
import base64, json, os, mimetypes, pathlib, sys, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = pathlib.Path(os.environ.get("PROJECT_DIR", os.getcwd()))
CARTOONS = ROOT / "cartoons"
CARTOONS.mkdir(exist_ok=True)
API_BASE = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"

def load_key() -> str:
    p = pathlib.Path.home() / ".runway/credentials"
    for line in p.read_text().splitlines():
        if line.startswith("RUNWAY_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("RUNWAY_API_KEY missing")

def encode_image(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"

def http(method, url, key, body=None):
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {key}",
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
    })
    try:
        return json.loads(urlopen(req, timeout=90).read())
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {url}\n{body}")

CARTOONS_SPEC = [
    # Use the best available band-members folder references for likeness
    ("06c", "Paul",   "ANGEL",  "band/band-members/paul.jpeg"),
    ("07c", "Rick",   "DEVIL",  "band/band-members/rick-2-good oen.jpg"),
    ("08c", "Mark",   "ANGEL",  "band/band-members/mark-sterns.jpg"),
    ("09c", "Shawn",  "DEVIL",  "members/shawn-kemp-lead.jpg"),     # no band-members photo
    ("10c", "Aiden",  "ANGEL",  "band/band-members/aiden-resized.jpg"),  # resized to <5MB
    ("11c", "Jason",  "DEVIL",  "band/band-members/jason-padded.jpg"),   # padded for ratio
]

def main():
    key = load_key()
    for cid, name, role, ref_path in CARTOONS_SPEC:
        out = CARTOONS / f"{cid}.png"
        if out.exists():
            print(f"[{cid}] skip (exists)")
            continue
        ref = ROOT / ref_path
        if not ref.exists():
            print(f"[{cid}] skip (no ref: {ref})")
            continue

        if role == "ANGEL":
            details = (
                "glowing golden halo above the head, large feathered angel wings extending behind, "
                "heavenly golden god-rays and soft white smoke in the background"
            )
        else:
            details = (
                "curved red devil horns on the head, sharp pointed devil tail, "
                "red and orange flames flickering behind, dark smoke and embers in the background"
            )

        prompt = (
            f"Stylized comic-book cartoon illustration of the MALE rock musician in the reference photo, "
            f"drawn as a rugged adult MAN — masculine features, square jaw, visible beard stubble or beard, "
            f"broad shoulders, rock-and-roll attire — as an {'angel' if role == 'ANGEL' else 'demon'} character "
            f"with {details}. "
            f"Keep the man's facial likeness, hairstyle, and beard clearly recognizable. "
            f"DO NOT render as a woman or feminine character. He is a male rock band member. "
            f"Dark dramatic illustration art style with bold lines, vivid colors, dramatic shading. "
            f"Full character visible from chest up, facing camera. No text, no logos."
        )

        body = {
            "model": "gen4_image",
            "ratio": "1280:720",
            "promptText": prompt,
            "referenceImages": [{"uri": encode_image(ref), "tag": "person"}],
        }
        print(f"[{cid}] submit  {name} as {role}")
        try:
            resp = http("POST", f"{API_BASE}/text_to_image", key, body)
        except Exception as e:
            print(f"[{cid}] ERROR: {e}")
            continue
        task_id = resp["id"]
        print(f"[{cid}] task_id={task_id}")

        delay = 5
        while True:
            info = http("GET", f"{API_BASE}/tasks/{task_id}", key)
            status = info.get("status")
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            print(f"  ... {status} (sleep {delay}s)")
            time.sleep(delay)
            delay = min(delay + 5, 30)

        if status != "SUCCEEDED":
            print(f"[{cid}] FAILED: {info.get('failure', {})}")
            continue
        urls = info.get("output", [])
        if not urls:
            print(f"[{cid}] no output URLs")
            continue
        with urlopen(urls[0], timeout=120) as r, open(out, "wb") as f:
            f.write(r.read())
        print(f"[{cid}] saved → {out}")

if __name__ == "__main__":
    main()
