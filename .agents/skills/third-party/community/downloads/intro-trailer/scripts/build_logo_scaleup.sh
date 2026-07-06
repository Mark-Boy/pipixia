#!/usr/bin/env bash
# Build clips/05.mp4 — logo scale-up animation per Paul's feedback.
# 303 logo starts ~5% scale, grows continuously to fill screen over 8 seconds.
# Background is the lightning+fire clip (04b) extended/looped to 8s.

set -euo pipefail
ROOT="${PROJECT_DIR:-$PWD}"
BG="$ROOT/clips/04b.mp4"
LOGO="$ROOT/logo/303-logo-2160.png"  # TRANSPARENT bg — no black rectangle around logo
OUT="$ROOT/clips/05.mp4"

if [[ ! -f "$BG" ]]; then
  echo "Error: $BG not ready yet — wait for Runway batch to finish 04b" >&2
  exit 1
fi
if [[ ! -f "$LOGO" ]]; then
  echo "Error: $LOGO missing" >&2
  exit 1
fi

# Logo aspect ratio = 1063:669 (~1.59:1). At full scale we fit to 1080 height:
# logo h=1080, logo w=1080*1.59=1717. So target dimensions: 1717x1080.
# scale expression: w='1717*(0.05+0.95*t/8)', h='1080*(0.05+0.95*t/8)'

ffmpeg -y -loglevel error \
  -stream_loop -1 -i "$BG" \
  -loop 1 -i "$LOGO" \
  -t 8 \
  -filter_complex "
    [0:v]scale=1920:1080:force_original_aspect_ratio=increase,
         crop=1920:1080,fps=24,format=yuva420p[bg];
    [1:v]format=rgba,
         scale=w='1717*(0.05+0.95*t/8)':h='1080*(0.05+0.95*t/8)':eval=frame[lg];
    [bg][lg]overlay=x='(W-w)/2':y='(H-h)/2':format=auto[v]
  " \
  -map "[v]" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -an \
  "$OUT"

dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUT")
echo "Scale-up saved: $OUT (${dur}s)"
