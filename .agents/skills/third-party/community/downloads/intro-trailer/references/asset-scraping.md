# Asset Scraping for Intro Trailers

How to pull logos, member photos, and crowd shots from band websites — even when they're behind Facebook auth walls.

## Logo extraction — inline SVG (modern sites)

Modern Astro/Next sites often inline the brand SVG directly in the homepage HTML rather than serving it as a separate file. The `<header>` `<svg>` block IS the logo.

```bash
# Grep for the inline SVG in the homepage HTML
curl -sS https://example.com/ | grep -oE '<svg[^>]*viewBox="0 0 [0-9]+ [0-9]+"[^>]*>.*?</svg>' | head -1
```

Or extract more reliably with Python:

```python
import re, urllib.request, pathlib
html = urllib.request.urlopen("https://example.com/").read().decode()
m = re.search(r'(<svg[^>]*viewBox="0 0 \d+ \d+"[^>]*>.*?</svg>)', html, re.S)
if m:
    pathlib.Path("logo/brand.svg").write_text(m.group(1))
```

**Identification:** the brand SVG usually has a large `viewBox` (e.g. `0 0 1063 669`). The favicon SVG is small (`0 0 32 32`). Don't confuse them.

## Logo rasterization

Once you have the SVG, render to PNG at multiple sizes/backgrounds:

```bash
# Transparent, 4K
rsvg-convert -h 2160 -b transparent logo/brand.svg -o logo/brand-2160.png

# Transparent, 1080p
rsvg-convert -h 1080 -b transparent logo/brand.svg -o logo/brand-1080.png

# On-black, 4K (for some Runway seeding scenarios)
rsvg-convert -h 2160 -b "#0a0a0a" logo/brand.svg -o logo/brand-onblack-2160.png
```

**Critical for ffmpeg scale-up:** use the **TRANSPARENT** PNG, not the on-black version. The on-black background creates a visible black rectangle when the logo scales up against a fire/lightning background.

## Member photo download — S3 / public bucket

If the band has a website-listed S3 bucket (very common), members are usually at predictable paths:

```bash
S3=https://bandmediabucket.s3.us-east-2.amazonaws.com
curl -fsSL -o members/singer.jpg "$S3/singer-name.jpg"
curl -fsSL -o members/drummer.jpg "$S3/drummer-name.jpg"
# ...
```

Inspect the band's `/the-band` page for image src URLs:

```bash
curl -sS https://example.com/the-band | grep -oE 'src="[^"]*\.(jpg|jpeg|png|webp)"' | sort -u
```

## Facebook gallery (the trick)

Most band sites embed Facebook's PhotoGallery widget. The photos themselves are served via `fbcdn.net` with signed URLs. Important: **these work without Facebook login but require the Referer header** matching the band's site.

```bash
# Find the gallery server-island endpoint in the homepage
curl -sS https://example.com/ | grep -oE 'href="/_server-islands/PhotoGallery[^"]*"'

# Fetch the gallery server island to get FB-CDN URLs
curl -sS "https://example.com/_server-islands/PhotoGallery?e=default&p=&s=%7B%7D" > gallery.html

# Extract fbcdn URLs
grep -oE 'https://scontent-[a-z0-9-]+\.xx\.fbcdn\.net/[^"]+\.jpg[^"]*' gallery.html
```

Download with Referer header:

```bash
curl -fsSL \
  -H "User-Agent: Mozilla/5.0" \
  -H "Referer: https://example.com/" \
  -o band/gallery/g01.jpg \
  "$FBCDN_URL"
```

**Without the Referer:** Facebook returns a 403 or a placeholder image.

**Signed URL expiry:** the `oe=` query param is a hex Unix timestamp. URLs typically expire in 1–7 days. Download them immediately; don't store the URLs for later.

## Hero video reference

Many band sites have a homepage hero video. It's the band's own visual identity statement — best reference for what "good" looks like for them.

```bash
# Find video src in homepage HTML
curl -sS https://example.com/ | grep -oE 'src="[^"]*\.(mp4|MP4|webm|mov)"' | sort -u

# Download
curl -fsSL -o band/hero-video/band-hero.mp4 "$VIDEO_URL"
```

Watch it before designing the trailer — you'll catch their preferred colors, lighting style, pace, and beats.

## Group photo / band lineup

A clear group photo with all members visible is invaluable for:
- Identifying which member is who when you have isolated portraits
- Generating "band assembled" shots in the trailer
- Establishing the band's visual aesthetic

Look for files named `band-pic`, `bandpic`, `group`, `lineup`, `full-band` on their S3 bucket or `/the-band` page.

## Contact sheet for visual triage

When you have 20+ photos to evaluate, build a contact sheet:

```bash
magick montage band/gallery/*.jpg \
  -tile 4x3 \
  -geometry 480x270+8+8 \
  -background black \
  band/gallery/contact-sheet.jpg

open band/gallery/contact-sheet.jpg
```

Then use the Read tool to view it and identify candidates.

## Identifying members from group shots

When member photos are mislabeled (common — websites get this wrong), use the band's own Facebook photo captions for ground truth:

```
"Rick is the guy with flame guitar here, Sterns is behind him holding a beer"
```

These captions are gold. Save them. They're the only way to disambiguate when a band has multiple bearded long-haired guys playing guitars (most rock bands).

## Resizing uploads for Runway

Phone screenshots and pro photos are usually too big for Runway's reference image limit (~5MB after base64). Resize before submitting:

```bash
# Standard pre-process for Runway reference uploads
magick big-source.png \
  -resize 1024x \             # ≤ 1024 wide (smaller dim)
  -quality 90 \               # decent compression
  -strip \                    # remove EXIF metadata (saves bytes)
  /tmp/cleaned.jpg
```

## What to gather (checklist before starting Phase 2)

- [ ] Logo SVG → rasterized PNG (transparent + on-black, multiple sizes)
- [ ] Member photos — 1 per cast member, clear face, no hat/sunglasses
- [ ] 8–12 crowd / gallery photos with variety (different venues, angles, eras)
- [ ] At least 1 group/band photo (full lineup)
- [ ] Optional: hero video from their site as reference
- [ ] Optional: existing graphics they like (album art, t-shirt designs, posters) for style cues

This is the asset baseline. Without it, the trailer will look generic. With it, the AI has the right anchors to lock onto.
