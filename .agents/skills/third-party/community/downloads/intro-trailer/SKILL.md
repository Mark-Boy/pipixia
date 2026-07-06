---
name: intro-trailer
description: Produce cinematic intro/walk-on trailers using Runway ML — live-show band intros, conference openers, product reveals, personal brand stingers. Generates Runway video clips, ffmpeg-composited scale-up animations, Ken Burns photo collages, optional cartoon character flashes, and a seamless final cut with unified color grade, ember overlay, vignette, grain, and variable crossfades. Use when the user says "/intro-trailer", "make an intro video", "make a band intro", "walk-on video", "live-show intro", "stage intro", "hype reel", "cinematic intro", "trailer with our logo", or asks for a multi-shot video built around a logo + cast members. Defaults to band/live-show pattern; documents adaptation to other use cases.
---

A cinematic intro/walk-on trailer playbook. Default deliverable is a 1080p H.264 silent MP4 (so the user can drop any track underneath) plus a ProRes HQ archive for venue rigs. Designed to scale a logo into the screen, reveal cast members, drop in real photo collages, and end on a tagline — all unified by a seamless finishing pass that makes 20+ generated clips feel like one continuous film.

This skill was extracted from the 303 band live-show intro project. Names below assume "band" but the same pipeline works for any cast (panelists, founders, team members, characters).

## Decision tree — when to use this skill

**Use this skill when:**
- The brief is a video built around a logo + cast/team reveals + atmosphere
- Length is 60–180 seconds (longer than social-video, shorter than a feature)
- The user wants it for a live performance, conference open, product launch, or similar "intro moment"
- Output must work without audio (silent so any track plays underneath) OR with a specific bundled track
- The user already has a logo file + member photos + maybe some crowd/event photos

**Don't use this skill for:**
- Short social clips (use the `social-video` skill — that's optimized for 9:16 and 15–60s)
- Music videos with synced cuts (this skill is silent-master by design)
- Live-action editing of existing footage (this is a generative AI pipeline, not an editor)
- Marketing explainer videos (different rhythm, different beat structure)

## The 9-act template (default band/event flow)

| Act | Time | Beat | Mode |
|---|---|---|---|
| I. The Hush | 0–4s | Pitch-black stage, single ember | t2v atmosphere |
| II. Heaven Cracks | 4–12s | Sky splits, god-rays, angel descends | t2v atmosphere |
| III. Hell Rises | 12–20s | Molten cracks, underworld figure rises | t2v atmosphere |
| IV. Collision | 20–25s | Winged silhouettes collide, white flash | t2v atmosphere |
| V. Logo Build | 25–40s | Lightning + fire build → logo grows from small to fill screen → BANG explosion | mixed t2v + ffmpeg scale-up + i2v |
| VI. Cast Reveals | 40–75s | Each member 5s with name lower-third + 1.5s cartoon flash | i2v |
| VII. Photo Collage | 75–97s | Real photos with Ken Burns motion | ffmpeg |
| VII-b. Event/Charity Beat | 97–107s | Event-specific moment (charity, signature show) | i2v |
| VIII. Cast Assembled | 107–117s | Full group with fire/sparks | i2v |
| IX. Final Stamp | 117–128s | Logo glow + tagline + URL | i2v + overlay |

**Adaptation:**
- Conference: replace "Heaven/Hell" atmosphere with industry imagery, member reveals → speaker reveals
- Product: replace cast with product features, photo collage with usage shots
- Personal brand: collapse cast to one person, lengthen atmosphere

## The seamless-composite secret (most important section)

Without this pass, the output reads as N stitched clips. With it, it reads as one film:

1. **Unified cinematic color grade** applied to every clip — crushed blacks, warm shadows (orange/red lift), gentle red boost in highlights, +contrast +saturation. ffmpeg `eq`+`colorbalance`+`curves`.
2. **Persistent ember/smoke overlay** at ~12% opacity running underneath every shot — even cast portraits. **Generate this layer once** via Runway `veo3.1 text_to_video` 8s, then loop across the whole video. This is the single biggest unifying element.
3. **Soft radial vignette** PNG overlaid on every shot.
4. **Light film grain** via ffmpeg `noise=alls=4:allf=t` per clip.
5. **Variable crossfade durations** — long dreamy 0.8s blends on atmosphere, hard 0.1s cut at the logo BANG, tight 0.3s flashes on cartoon inserts, 0.4–0.5s on cast reveals.

Full reference: `references/seamless-pipeline.md`. Scripts: `scripts/composite_seamless.py`.

## Critical Runway API constraints (every one of these caused a failure in the 303 build)

These are the constraints that will silently break a generation if violated. Reference: `references/runway-api-constraints.md`.

**Video gen — duration constraints (per model):**
| Model | Mode | Allowed durations |
|---|---|---|
| `gen3a_turbo` | i2v, t2v | 5, 10 |
| `gen4_turbo` | i2v ONLY (no t2v) | 5, 10 |
| `gen4.5` | t2v | 5 |
| `veo3` | t2v | 8 |
| `veo3.1` | t2v, i2v | 8 |
| `veo3.1_fast` | t2v | 4, 6, 8 |
| `kling*` | varies | check API |
| `seedance2` | t2v | check API |

**Video gen — ratio constraints (gen4_turbo accepts these only):**
`1280:720` (16:9), `720:1280` (9:16), `1104:832` (4:3), `832:1104` (3:4), `960:960` (1:1), `1584:672` (21:9).
The composite pipeline upscales `1280:720` to `1920:1080` in post. Do NOT submit `1920:1080`.

**Image gen reference image rules:**
- File size: must be < ~5 MB after base64 (3.9 MB raw safe upper bound)
- Aspect ratio: `width / height >= 0.5` (taller than 2:1 portrait fails)
- Format: JPG or PNG accepted; `.PNG` (uppercase) extension works
- Pre-process tall iPhone screenshots: pad with black or crop before submission

**Content moderation gotchas:**
- "devil" gets flagged on `veo3.1` — use "horned warrior silhouette" or "primal shadow figure"
- "blood", "gore", "demon" similar — keep descriptions stylized

**Required headers on every call:**
```
Authorization: Bearer ${RUNWAY_API_KEY}
X-Runway-Version: 2024-11-06
Content-Type: application/json
```

**Billing:** `api.dev.runwayml.com` is billed separately from `app.runwayml.com`. Fund credits at `dev.runwayml.com/billing` — an active subscription does NOT fund API calls.

## Workflow (start to finish)

### Phase 1: Asset gathering

1. **Logo** — extract or download. If the band site uses inline SVG (common with Astro/modern sites), grep the homepage HTML for `<svg[^>]*viewBox=` and save the matched block. Render to PNG with `rsvg-convert -h 2160 -b transparent` for the transparent version AND `-b "#0a0a0a"` for an on-black version. Both go in `logo/`.
2. **Cast photos** — preferably isolated head-and-shoulder shots, face clearly visible, no hat/sunglasses (these obscure features and the cast will say "doesn't look like him"). If only group shots exist, crop tightly to each face. Save in `members/{name-role}.jpg`.
3. **Crowd / event photos** — for the collage. 8–12 strong photos covering different venues / events / angles. If sourcing from Facebook (their official `PhotoGallery` widget proxies through `fbcdn.net`), download with `curl -H "Referer: https://theirsite.com/"` — the signed URLs work without login but require the referer header.
4. **Reference photos for cartoons** — same as cast photos, but with extra emphasis on facial features. The AI will misread feminine-looking long-hair photos as women unless the prompt explicitly says "MALE rock musician" (see `references/cartoon-prompts.md`).

### Phase 2: Shot definition

Edit `templates/prompts.json` to your project. Each shot has:
```json
{
  "id": "06",
  "act": "VI. Cast Reveals — Singer",
  "timeRange": "40-45",
  "duration": 5,
  "mode": "image_to_video",
  "model": "gen4_turbo",
  "ratio": "1280:720",
  "seedImage": "members/paul-vocals.jpg",
  "promptText": "Slow cinematic push-in on the man in the frame. Subtle dramatic backlight, drifting smoke around him. Keep his face and identity exactly as shown — do not change his features. Concert film look.",
  "lowerThird": { "name": "PAUL WILLIAMS", "role": "VOCALS" }
}
```

Optional fields:
- `runwayDuration: 5` — if Runway requires a different duration than the composite display duration (e.g. cartoon flashes display 1.5s but submit at 5s)
- `cartoonRole: "ANGEL"` / `"DEVIL"` — for cartoon flash shots
- `endTagCard` — metadata only, composite uses `tagline_card.png` overlay

### Phase 3: Generate

```bash
export PROJECT_DIR=~/clientname-intro
python3 ~/.claude/skills/intro-trailer/scripts/generate.py
```

The generator iterates all shots in `prompts.json`, fires Runway API calls in sequence, polls until done, and downloads MP4s. It skips shots that already exist (resumable), skips `ffmpeg_*` modes (handled later), and skips shots whose seed image isn't ready (e.g. cartoons before their PNG is generated).

For cartoon images (used as seeds for cartoon flash shots):
```bash
python3 ~/.claude/skills/intro-trailer/scripts/generate_cartoons.py
```

### Phase 4: ffmpeg-composited assets

These are built locally with no Runway calls:

- **Logo scale-up animation** (shot V — Paul-style "starts small, fills screen"):
  ```bash
  bash ~/.claude/skills/intro-trailer/scripts/build_logo_scaleup.sh
  ```
  Uses the lightning+fire clip as background, scales the TRANSPARENT logo PNG from 5% → 100% over 8 seconds.
  **Critical:** use the transparent logo (`303-logo-2160.png`), NOT the on-black version. The on-black PNG creates a visible black rectangle as the logo scales up.

- **Ember overlay layer** (single 8s clip via Runway, then looped under every shot):
  ```bash
  python3 ~/.claude/skills/intro-trailer/scripts/build_ember_overlay.py
  ```
  Output: `overlays-source/embers-veo31-8s.mp4` (~75 credits to generate).

- **Photo collage** (Ken Burns slow pan/zoom):
  ```bash
  python3 ~/.claude/skills/intro-trailer/scripts/build_collage.py
  ```
  Edit the `PHOTOS` list inline. 2.5s per photo with 0.5s crossfades reads well. Output → `clips/12.mp4`.

- **Overlay PNGs** (lower-thirds + tagline card + vignette):
  ```bash
  bash ~/.claude/skills/intro-trailer/scripts/render_overlays.sh
  ```
  Pre-renders text as transparent PNGs because most Homebrew ffmpeg builds lack `drawtext` (no freetype). Composited via the `overlay` filter instead. Always use this approach unless you've verified your ffmpeg has `drawtext`.

### Phase 5: Final seamless composite

```bash
python3 ~/.claude/skills/intro-trailer/scripts/composite_seamless.py
```

This is the magic. Each clip goes through:
1. Scale + pad to 1920×1080 @ 24fps
2. Color grade pass
3. Ember overlay at 12% opacity
4. Vignette overlay
5. Light grain via noise filter
6. (member shots only) lower-third PNG overlaid with fade-in
7. (final shot only) tagline + URL card overlaid

Then all clips are chained with variable xfade durations per the `XFADE` dict.

Output: `output/303-intro-1080p.mp4` + `output/303-intro-1080p-prores.mov`.

## Cost estimate (typical band intro, ~130s output)

| Item | Credits |
|---|---|
| 4 atmosphere t2v clips (veo3.1 @ 75/clip) | ~300 |
| 1 logo lightning+fire t2v (veo3.1) | 75 |
| 1 ember overlay t2v (veo3.1) | 75 |
| 1 logo explosion i2v (gen4_turbo) | 25 |
| 6 cast reveals i2v (gen4_turbo @ 25/clip) | 150 |
| 6 cartoon images (gen4_image @ 10/clip) | 60 |
| 6 cartoon animations i2v (gen4_turbo @ 25/clip) | 150 |
| 1 event/charity i2v (gen4_turbo) | 25 |
| 1 cast-assembled i2v (gen4_turbo, 10s) | 50 |
| 2 final-logo i2v (gen4_turbo @ 25/clip) | 50 |
| **Subtotal** | **~960 credits (~$9–12)** |
| Iteration buffer (re-fires, prompt tuning) | +200–500 credits |
| **Realistic total** | **~1500 credits (~$15–18)** |

Always check `creditBalance` from `/v1/organization` before starting a full run.

## Common iteration gotchas (saved from 303 project pain)

1. **"Doesn't look like him"** — cast members will universally say this on first cut. Plan for ≥1 round of seed-photo swaps. Real-world fix: ask the client for phone selfies, no hat, no sunglasses, face clear.
2. **Logo with black rectangle around it** — happens when the on-black logo PNG is used as a seed or in an ffmpeg overlay. Use the TRANSPARENT logo PNG (`303-logo-2160.png` style).
3. **Cartoon misreads gender** — long-haired men render as women without explicit "MALE rock musician, masculine features, beard stubble" language. See `references/cartoon-prompts.md`.
4. **Old text leaks through** — when iterating, always re-run the full composite pipeline, never trust the cached output. Tag cards from a previous design show through if not fully rebuilt.
5. **Live-show client wants the tagline back** — Kevin's preference was to drop big tag cards in favor of just a URL. The 303 client (Paul) wanted "KICK ASS ROCK AND ROLL 2026" back. Ask the client AND the brand decision-maker — they may have different opinions.
6. **Iteration cycle** — first cut → big-picture feedback → second cut → likeness fixes + new beats → third cut → tagline + polish. Plan for 3 cuts minimum.

## Quick reference — file structure

A project built with this skill should look like:

```
~/clientname-intro/
├── STORYBOARD.md
├── logo/
│   ├── client-logo.svg
│   ├── client-logo-1080.png         # transparent
│   ├── client-logo-2160.png         # transparent — use for ffmpeg scale-up
│   └── client-logo-onblack-2160.png # on-black background
├── members/
│   └── {name-role}.jpg              # one per cast member
├── band/                            # other source photos
│   ├── gallery/                     # collage candidates
│   ├── band-members/                # alternate reference photos
│   ├── hero-video/                  # any existing reference video
│   └── crowd/                       # extra crowd shots
├── cartoons/
│   └── {id}.png                     # generated cartoon portraits
├── overlays-source/
│   └── embers-veo31-8s.mp4          # ember overlay clip
├── clips/
│   └── {id}.mp4                     # one per shot in prompts.json
├── output/
│   ├── overlays/                    # PNGs (lower-thirds, vignette, tagline)
│   ├── tmp/                         # composite intermediates
│   ├── intro-1080p.mp4              # final H.264 deliverable
│   └── intro-1080p-prores.mov       # ProRes for venue rigs
└── scripts/                         # symlinks or copies from this skill
```

## Adapting for non-band projects

- **Conference opener** — drop the heaven/hell cosmology, use industry-themed atmosphere (cityscapes, dawn, datacenter, etc.). Member reveals become speaker reveals. Photo collage becomes past-event photos. End on event name + dates instead of band name.
- **Product launch** — atmosphere is product-themed (manufacturing imagery, the problem being solved). Cast reveals become founder/team. Photo collage becomes usage scenarios. End on product name + tagline + URL.
- **Personal brand** — single cast member, longer atmosphere, photo collage of personal milestones. End on personal name + tagline + URL.
- **Wedding** — atmosphere is ceremony-themed, cast reveals are the couple + wedding party, collage is venue + planning moments. Family-friendly tone, no devils.

## References

- `references/runway-api-constraints.md` — every constraint that broke us, with the exact error message
- `references/seamless-pipeline.md` — deep dive on the color grade, ember overlay, variable crossfades
- `references/cartoon-prompts.md` — prompt templates for character cartoons, gender accuracy notes
- `references/asset-scraping.md` — how to pull from band websites, FB-CDN, inline SVG logos
- `references/shot-templates.md` — copy-paste shot definitions for common beats
- `templates/prompts.json` — starter shot list with all 9 acts populated
