#!/usr/bin/env bash
# Render lower-third and tag-card PNGs at 1920x1080 with transparent background.
# Used by composite.sh since this ffmpeg build lacks drawtext (no freetype).

set -euo pipefail
ROOT="${PROJECT_DIR:-$PWD}"
OUT="$ROOT/output/overlays"
mkdir -p "$OUT"

FONT_IMPACT="/System/Library/Fonts/Supplemental/Impact.ttf"
FONT_BODY="/System/Library/Fonts/HelveticaNeue.ttc"

# Lower-third: black 55%-alpha rectangle bottom-left, NAME big white, ROLE smaller gold
lower_third() {
  local out="$1" name="$2" role="$3"
  magick -size 1920x1080 xc:none \
    -fill 'rgba(0,0,0,0.55)' -draw "rectangle 80,890 980,1020" \
    -fill white -font "$FONT_IMPACT" -pointsize 64 \
    -draw "text 110,970 '$name'" \
    -fill '#e5ae16' -font "$FONT_BODY" -pointsize 32 \
    -draw "text 112,1010 '$role'" \
    PNG32:"$out"
}

lower_third "$OUT/lt_06.png" "PAUL WILLIAMS"  "VOCALS"
lower_third "$OUT/lt_07.png" "RICK PISCIA"    "RHYTHM GUITAR"
lower_third "$OUT/lt_08.png" "MARK STEARNS"   "LEAD / RHYTHM"
lower_third "$OUT/lt_09.png" "SHAWN KEMP"     "LEAD GUITAR"
lower_third "$OUT/lt_10.png" "AIDEN HALLETT"  "BASS"
lower_third "$OUT/lt_11.png" "JASON MANCINI"  "DRUMS"

# Final URL card: clean understated website at bottom of frame with subtle shadow
magick -size 1920x1080 xc:none \
  -font "$FONT_BODY" -pointsize 44 \
  -fill 'rgba(255,255,255,0.9)' \
  -gravity south -annotate +0+60 'https://303band.com' \
  -gravity south -annotate +2+58 'https://303band.com' \
  PNG32:"$OUT/url_card.png"

# Re-render with proper drop shadow (shadow first, then white text on top)
magick -size 1920x1080 xc:none \
  -font "$FONT_BODY" -pointsize 44 \
  -fill 'rgba(0,0,0,0.7)' -gravity south -annotate +3+57 'https://303band.com' \
  -fill 'rgba(255,255,255,0.95)' -gravity south -annotate +0+60 'https://303band.com' \
  PNG32:"$OUT/url_card.png"

# Final tagline card: "KICK ASS ROCK AND ROLL 2026" tasteful tagline + URL underneath
# Style: elegant letterspaced sans-serif (Futura Bold), drop shadow, white/gold combo
# Logo stays prominent; tagline sits below mid-frame; URL at very bottom
FONT_TAGLINE="/System/Library/Fonts/Supplemental/Futura.ttc"
magick -size 1920x1080 xc:none \
  -font "$FONT_TAGLINE" -pointsize 64 -kerning 8 \
  -fill 'rgba(0,0,0,0.6)' -gravity center -annotate +3+243 'KICK ASS ROCK AND ROLL 2026' \
  -fill 'rgba(255,255,255,0.96)' -gravity center -annotate +0+240 'KICK ASS ROCK AND ROLL 2026' \
  -font "$FONT_BODY" -pointsize 36 -kerning 0 \
  -fill 'rgba(0,0,0,0.7)' -gravity south -annotate +3+57 'https://303band.com' \
  -fill 'rgba(255,255,255,0.9)' -gravity south -annotate +0+60 'https://303band.com' \
  PNG32:"$OUT/tagline_card.png"

ls -la "$OUT"
