#!/usr/bin/env python3
"""
Build a Ken Burns photo collage from 7 real concert/crowd photos.
Output: ~/303band-intro/clips/12.mp4 (replaces the AI crowd shot in shot 12).

Each photo runs 1.5s with subtle zoom + slight pan. 0.3s xfade between photos.
Net runtime: ~9s.
"""
import os, pathlib, subprocess, sys

ROOT = pathlib.Path(os.environ.get("PROJECT_DIR", os.getcwd()))
GALLERY = ROOT / "band/gallery"
BAND_MEMBERS = ROOT / "band/band-members"
TMP = ROOT / "output/tmp-collage"
OUT = ROOT / "clips/12.mp4"

# Extended collage per Paul's feedback: slow down + more photos
# Order chosen for energy arc (open big → variety → iconic close)
PHOTOS = [
    (GALLERY, "g01-492171434_1244886764.jpg"),   # stage with flame effect
    (GALLERY, "g04-492942663_1244886594.jpg"),   # band + outdoor fans
    (BAND_MEMBERS, "482032373_1203251088468536_893984521200085982_n.jpg"),  # full stage band shot
    (GALLERY, "g02-488942958_2618356335.jpg"),   # B&W moody stage
    (BAND_MEMBERS, "488256348_1224499736343671_8614402807154347894_n.jpg"), # concert crowd
    (GALLERY, "g06-489417932_2618356108.jpg"),   # yellow lights crowd
    (BAND_MEMBERS, "485073914_1210519377741707_4981114513183865155_n.jpg"), # American flag patriotic
    (GALLERY, "g03-492470061_1244886560.jpg"),   # crowd selfie with band
    (BAND_MEMBERS, "490799630_1236640248462953_7516677120130389162_n.jpg"), # crowd shot
    (GALLERY, "g08-492503088_1245011610.jpg"),   # wide crowd at venue
    (GALLERY, "g07-491954886_1245011600.jpg"),   # 303 logo + crowd (iconic close)
]

CLIP_DUR = 2.5      # seconds per photo (slowed per Paul's feedback)
XFADE = 0.5         # crossfade overlap between photos
FPS = 24
FRAMES = int(CLIP_DUR * FPS)

TMP.mkdir(parents=True, exist_ok=True)

# 1) Render each photo as a Ken Burns clip
print(f"Rendering {len(PHOTOS)} Ken Burns sub-clips...")
sub_clips = []
for i, entry in enumerate(PHOTOS):
    folder, name = entry
    src = folder / name
    if not src.exists():
        sys.exit(f"missing photo: {src}")
    dst = TMP / f"kb_{i:02d}.mp4"
    # Alternate zoom direction for variety
    if i % 2 == 0:
        # zoom-in: 1.0 → 1.12
        zoom_expr = f"min(zoom+{0.12/FRAMES:.5f},1.12)"
    else:
        # zoom-out: 1.12 → 1.0 (start zoomed, pull back)
        zoom_expr = f"max(zoom-{0.12/FRAMES:.5f},1.0)"
    vf = (
        # First scale up so the zoompan has pixels to work with
        f"scale=2880:1620:force_original_aspect_ratio=increase,"
        f"crop=2880:1620,"
        # Zoompan with the chosen zoom expression
        f"zoompan=z='{zoom_expr}':d={FRAMES}:s=1920x1080:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={FPS}"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(src),
        "-t", str(CLIP_DUR), "-r", str(FPS),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(dst)
    ], check=True)
    sub_clips.append(dst)

# 2) Chain with xfade dissolves into the combined collage clip
print("Chaining with xfade dissolves...")
inputs = []
for c in sub_clips:
    inputs += ["-i", str(c)]

chain = []
prev_label = "[0:v]"
cum_offset = 0.0
for i in range(1, len(sub_clips)):
    if i == 1:
        cum_offset = CLIP_DUR - XFADE
    else:
        cum_offset += CLIP_DUR - XFADE
    out_label = f"[v{i}]"
    chain.append(
        f"{prev_label}[{i}:v]xfade=transition=fade:duration={XFADE}:"
        f"offset={cum_offset:.3f}{out_label}"
    )
    prev_label = out_label

filter_complex = ";".join(chain)
final_label = prev_label

subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error",
    *inputs,
    "-filter_complex", filter_complex,
    "-map", final_label,
    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
    "-pix_fmt", "yuv420p", "-an",
    str(OUT)
], check=True)

# Report duration
result = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", str(OUT)
], capture_output=True, text=True)
dur = float(result.stdout.strip())
print(f"\nCollage saved: {OUT}")
print(f"Duration: {dur:.2f}s")
print(f"  → update prompts.json shot 12 duration to {dur:.1f}")
