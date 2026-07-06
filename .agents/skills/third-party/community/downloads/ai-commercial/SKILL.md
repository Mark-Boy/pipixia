---
name: ai-commercial
description: Produce quick commercials (30-90s) for SaaS products, local services, personal brand, and product launches by combining Runway ML generative video, ElevenLabs voiceover, procedural music, and ffmpeg composition. Hybrid pipeline that uses Runway for cinematic hero shots and AI B-roll, social-video patterns for VO + music + slides, and a brand-aware composite with multi-aspect export. Use when the user says "/ai-commercial", "make a commercial", "make an ad", "TV-style ad", "commercial for [client]", "60-second spot", "promo ad", or asks for a paid-media-grade video built around a product or service. Distinct from /intro-trailer (live-show hype reels, silent) and /social-video (text/screenshot-driven reels with VO).
---

A commercial-grade ad pipeline. Combines the best of two worlds:

- **Generative cinematic shots** via Runway ML (Veo, Gen4, ElevenLabs proxy) — for hero moments, atmosphere, B-roll where stock footage would otherwise be needed.
- **VO + music + slide composition** via direct ElevenLabs API + ffmpeg — for the structural backbone of a commercial (narration, CTA, brand reveal).

Default output: 30-90s commercial with VO + music + brand grade + CTA, in whatever aspect ratio the brief specifies (typically 16:9 for web/YouTube, 9:16 for IG/TikTok stories, 1:1 for IG feed).

## Decision tree — which skill to use

| Brief | Skill |
|---|---|
| Live show walk-on / stage intro, silent | `intro-trailer` |
| Blog post → social reel with VO + screenshots | `social-video` (mode: slide) |
| App demo walkthrough with screenshots | `social-video` (mode: demo) |
| Brand launch trailer | `social-video` (mode: trailer) OR `ai-commercial` if heavy AI B-roll |
| **TV-style commercial with VO + AI cinematic shots + CTA** | **`ai-commercial`** ← you are here |
| Wedding / event sizzle | `ai-commercial` (personal-brand template, adapted) |

## The commercial workflow

A commercial has a fixed beat structure (you can break it, but most don't):

1. **HOOK** (3-5s) — cinematic Runway shot or product close-up that stops the scroll
2. **PROBLEM / SETUP** (5-15s) — VO over screenshots, lifestyle imagery, or AI B-roll
3. **SOLUTION / OFFER** (15-40s) — product walkthrough, value props, benefits
4. **PROOF** (optional 5-15s) — testimonial placeholders, logos, stats
5. **CTA** (5-10s) — logo + URL + offer + voice "Visit example.com today"

All 4 templates in this skill use a variant of this structure.

## 4 templates (start here for each commercial)

```
templates/
├── saas-demo.json         # 45-60s SaaS commercial
├── local-service.json     # 30s service ad (plumber, restaurant, etc.)
├── personal-brand.json    # 45-60s "who I am" / hire-me piece
└── product-launch.json    # 60-90s digital product launch trailer
```

Each template defines:
- Default duration
- Default aspect ratio (overrideable per project)
- Scene list with type, duration, copy placeholders
- Voice characteristics (gender, age, tone)
- Music style hint

Copy a template into your project as `brief.json`, fill in the placeholders, run.

## Quick start

```bash
# 1. Set up project
mkdir -p ~/clientname-commercial/{assets,brief,output}
cp ~/.claude/skills/ai-commercial/templates/saas-demo.json ~/clientname-commercial/brief/brief.json

# 2. Fill in the brief (or edit interactively — see "The brief schema" below)

# 3. Place assets in the project
cp logo.png ~/clientname-commercial/assets/logo.png
cp product-screenshot.png ~/clientname-commercial/assets/screenshot1.png
# ... etc

# 4. Run
export PROJECT_DIR=~/clientname-commercial
python3 ~/.claude/skills/ai-commercial/scripts/make_commercial.py
```

`make_commercial.py` reads `brief/brief.json`, dispatches each scene by type, composes the final commercial(s) in the requested aspect ratios, and saves to `output/commercial-{aspect}.mp4`.

## The brief schema

The brief is a JSON file describing the entire commercial. Full schema in `references/brief-schema.md`. The essential fields:

```json
{
  "type": "saas-demo",
  "duration": 60,
  "aspectRatios": ["16:9", "9:16"],
  "voice": {
    "voice_id": "ELEVENLABS_VOICE_ID_HERE_OR_USE_DEFAULT",
    "style": "commercial-narrator",
    "stability": 0.5,
    "similarity_boost": 0.75
  },
  "music": {
    "style": "cinematic",
    "volume": 0.25
  },
  "brand": {
    "name": "ClientName",
    "logo": "assets/logo.png",
    "tagline": "Their tagline",
    "url": "https://example.com",
    "primaryColor": "#3b82f6",
    "accentColor": "#8b5cf6"
  },
  "scenes": [
    {
      "id": "hook",
      "duration": 5,
      "type": "runway_atmosphere",
      "prompt": "Cinematic close-up of a developer's hands typing on a sleek mechanical keyboard, soft blue and purple LED light from the screen, shallow depth of field, slow push-in."
    },
    {
      "id": "problem",
      "duration": 8,
      "type": "screenshot_kenburns",
      "image": "assets/old-spreadsheet.png",
      "vo": "Tired of managing your client invoices in a spreadsheet?",
      "motion": "zoom_in"
    },
    {
      "id": "solution",
      "duration": 20,
      "type": "screenshot_kenburns",
      "image": "assets/clientname-dashboard.png",
      "vo": "ClientName replaces your spreadsheet with a beautiful dashboard that actually does the work for you.",
      "motion": "pan_right"
    },
    {
      "id": "broll-1",
      "duration": 5,
      "type": "runway_i2v",
      "seedImage": "assets/team-photo.jpg",
      "prompt": "Slow camera push-in on the team, subtle smiles, warm office lighting, shallow depth of field.",
      "vo": "Built by people who understand your business."
    },
    {
      "id": "cta",
      "duration": 6,
      "type": "cta_slide",
      "headline": "Try it free for 14 days",
      "subhead": "No credit card required",
      "vo": "Visit examplebrand.com today.",
      "ctaUrl": "examplebrand.com"
    }
  ]
}
```

## Scene types (dispatcher contract)

`make_commercial.py` dispatches scenes by `type`:

| `type` | What it does | Fields used |
|---|---|---|
| `runway_atmosphere` | Generates a text-to-video clip via Runway | `prompt`, `duration` |
| `runway_i2v` | Image-to-video animation of a seed image | `seedImage`, `prompt`, `duration` |
| `screenshot_kenburns` | Ken Burns motion on a still image with VO overlaid | `image`, `motion`, `vo`, `duration` |
| `logo_reveal` | ffmpeg logo scale-up animation | `logo` (from brand), `duration` |
| `cta_slide` | Designed CTA card with logo + URL + headline | `headline`, `subhead`, `ctaUrl`, `vo` |
| `bumper` | 2-3s branded interstitial (color + logo + sting SFX) | `color`, `sfx` |
| `testimonial` | Quote + name + photo card | `quote`, `name`, `photo` |
| `screen_recording` | Pre-recorded screen capture playback | `video`, `vo` |

If a scene has a `vo` field, ElevenLabs synthesizes it and the VO is overlaid on the scene's visuals. Music is added underneath at `music.volume` and DUCKED to ~0.4× during VO segments.

## Voice selection (per commercial)

ElevenLabs voice IDs determine the commercial's personality. The skill defaults to `$ELEVENLABS_VOICE_ID` (your env default), but each brief can override:

- **Commercial narrator** — Adam (`pNInz6obpgDQGcFmaJgB`) — deep male, authoritative
- **Warm female** — Rachel (`21m00Tcm4TlvDq8ikWAM`) — warm, friendly
- **Energetic male** — Antoni (`ErXwobaYiN019PkySvjV`) — younger, upbeat
- **Calm female** — Domi (`AZnzlk1XvdvUeBnXmlld`) — soft, intimate
- **British male** — Daniel (`onwK4e9ZLuTAKqWW03F9`) — refined, polished

Full reference: `references/voice-selection.md`. For each commercial, pick the voice that matches the brand personality. Local plumber → energetic male. Luxury watch brand → British male. Therapy app → calm female.

## Music style hints

The `music.style` field in the brief drives the procedural music generator:

| `style` | Vibe | Best for |
|---|---|---|
| `cinematic` | Building strings, drop at CTA | SaaS, product launches |
| `upbeat` | Drums + bass, high tempo | Local service ads, food/retail |
| `ambient` | Soft pads, minimal | Personal brand, healthcare |
| `electronic` | Synths, modern pulse | Tech products, agencies |
| `acoustic` | Guitar, organic | Wellness, lifestyle |

Music plays underneath the entire commercial at `music.volume` (typically 0.20-0.30), with automatic ducking when VO is active. The bed is **auto-generated** by `scripts/generate_music.py` (which reuses social-video's procedural NumPy synth) — no manual step. `cinematic` and `ambient` are fully implemented; other styles fall back to cinematic until upstream adds them. Full reference: `references/music-pairing.md`.

## Aspect ratio export

Each commercial can be rendered in multiple aspect ratios in one run. The brief lists them in `aspectRatios`:

```json
"aspectRatios": ["16:9", "9:16", "1:1"]
```

For each ratio, `make_commercial.py`:
1. Re-composes scenes (Runway clips may need re-crop/re-frame for vertical)
2. Adjusts text overlay positions for the canvas
3. Outputs `output/commercial-16x9.mp4`, `output/commercial-9x16.mp4`, `output/commercial-1x1.mp4`

The 16:9 master is the source of truth; 9:16 and 1:1 are smart-crop derivations (center-of-interest crop where possible, letterboxing only as last resort).

## Cost estimate

Typical 60s commercial with 6 scenes:

| Item | Cost |
|---|---|
| 2 Runway atmosphere/B-roll clips (gen4.5 + gen4_turbo i2v) | ~50 Runway credits ($0.50) |
| 1 Runway hero shot (veo3.1 8s) | ~75 Runway credits ($0.75) |
| ~80 seconds of ElevenLabs VO | ~3000 chars × $0.30/1K = $0.90 |
| Procedural music | $0 |
| ffmpeg composition | $0 |
| 3 aspect ratio re-renders | $0 |
| **Total** | **~$2.15 per commercial** |

Plus iteration buffer (likely 1-2 rounds of VO re-takes, maybe 1 Runway shot re-fire): ~$1-2 extra. Realistic: **$3-5 per commercial**.

## Common iteration gotchas

1. **VO timing mismatch** — VO turns out shorter/longer than the scene duration. Fix: regenerate VO with adjusted text length, or stretch/shrink scene duration in the brief.
2. **Runway prompt doesn't land** — the AI generates something off. Fix: be more specific about composition ("close-up of hands typing" vs "person at computer"), add style modifiers ("shallow depth of field, slow push-in").
3. **Music drowns the VO** — bump `music.volume` down to 0.18, or increase the duck depth in `make_commercial.py`.
4. **Aspect crop loses the subject** — for 9:16 / 1:1, sometimes the auto-crop misses the focal point. Override per scene with explicit `cropFocus: {x: 0.5, y: 0.4}`.
5. **CTA URL doesn't read** — bump CTA font size, increase shadow contrast against the background.
6. **Brand colors clash with AI footage** — Runway output is wildly variable on color. Apply a brand-color grade pass in `make_commercial.py` so all scenes lean toward your brand palette.

## When NOT to use this skill

- Pure screenshot-driven content with no AI B-roll → use `social-video` directly (cheaper, faster)
- Live performance / venue intro → use `intro-trailer`
- Talking-head with real footage → out of scope (just edit in DaVinci/Premiere)
- Music video / synced cuts to music → out of scope (this is silent-master under VO)

## File structure

A commercial project should look like:

```
~/clientname-commercial/
├── brief/
│   └── brief.json                # the spec — single source of truth
├── assets/                       # user-provided
│   ├── logo.png
│   ├── screenshot1.png
│   ├── screenshot2.png
│   ├── team-photo.jpg
│   └── ...
├── generated/                    # AI-generated intermediates
│   ├── runway/                   # Runway video clips
│   │   ├── scene-01-hook.mp4
│   │   └── scene-04-broll.mp4
│   ├── vo/                       # ElevenLabs VO audio
│   │   ├── scene-02-vo.mp3
│   │   └── scene-03-vo.mp3
│   ├── music/
│   │   └── bed.mp3               # procedural music bed
│   ├── overlays/                 # PNG title cards, CTAs
│   │   └── cta-slide.png
│   └── scenes/                   # per-scene composited MP4s
│       ├── 01-hook.mp4
│       ├── 02-problem.mp4
│       └── ...
└── output/
    ├── commercial-16x9.mp4       # final deliverables
    ├── commercial-9x16.mp4
    └── commercial-1x1.mp4
```

## References

- `references/brief-schema.md` — complete brief.json schema, every field documented
- `references/voice-selection.md` — voice ID library, gender/tone/use-case mapping
- `references/music-pairing.md` — music style → commercial type pairing rules
- `references/workflow-hybrid.md` — how Runway + ElevenLabs + ffmpeg interact, the orchestrator state machine

## Triggers (auto-invocation)

This skill triggers when the user says:
- `/ai-commercial`, `/commercial`, `/ad`
- "make a commercial"
- "make an ad"
- "TV-style ad", "60-second spot", "promo ad"
- "commercial for [client]" / "ad for [brand]"
- "paid media ad", "Google Ads video", "Facebook ad video"
