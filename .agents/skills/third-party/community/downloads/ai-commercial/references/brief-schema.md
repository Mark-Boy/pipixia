# brief.json Schema

Every commercial built with this skill is defined by a single `brief.json`. This is the source of truth — the orchestrator reads it, dispatches scenes, composites the final output.

## Top-level fields

```jsonc
{
  "type": "saas-demo",         // template type — informational, not enforced
  "duration": 60,              // total seconds — sum of scene durations should match
  "aspectRatios": ["16:9", "9:16"],  // exports to generate
  "voice": { ... },            // ElevenLabs VO config
  "music": { ... },            // music bed config
  "brand": { ... },            // brand colors, logo, URL
  "scenes": [ ... ]            // ordered list of scenes
}
```

## `voice` — ElevenLabs config

```jsonc
{
  "voice_id": "21m00Tcm4TlvDq8ikWAM",  // ElevenLabs voice ID; blank = use $ELEVENLABS_VOICE_ID env
  "style": "commercial-narrator",       // informational label
  "stability": 0.5,                     // 0.0-1.0; lower = more variable/emotive, higher = more consistent
  "similarity_boost": 0.75,             // 0.0-1.0; how closely to match the voice's training samples
  "model_id": "eleven_multilingual_v2"  // optional; default is multilingual v2
}
```

For voice IDs, see `voice-selection.md`. Use higher stability (0.6-0.7) for narrators, lower (0.3-0.5) for energetic/emotional reads.

## `music` — music bed config

```jsonc
{
  "style": "cinematic",  // cinematic | upbeat | ambient | electronic | acoustic | none
  "volume": 0.25         // 0.0-1.0; level of music under the VO. 0.20-0.30 is typical.
}
```

If `style: "none"`, no music is mixed.

The orchestrator looks for a music bed at `$PROJECT_DIR/generated/music/bed.mp3`. If absent, integrate `social-video`'s procedural music generator (TODO) or drop in a royalty-free bed manually.

## `brand` — brand assets and colors

```jsonc
{
  "name": "ClientName",
  "logo": "assets/logo.png",        // path relative to PROJECT_DIR
  "tagline": "Their tagline",
  "url": "https://example.com",
  "phone": "555-555-5555",           // optional, for local-service ads
  "launchOffer": "...",              // optional, for product-launch ads
  "primaryColor": "#3b82f6",
  "accentColor": "#8b5cf6"
}
```

Brand colors flow into CTA card backgrounds, accent text colors, and the overall color grade. Use hex codes with `#` prefix.

## `scenes` — the ordered scene list

Each scene is a single beat in the commercial. Total scene durations should equal the top-level `duration`.

### Common scene fields

```jsonc
{
  "id": "hook",                    // unique within the brief
  "duration": 5,                   // seconds in the final commercial
  "type": "runway_atmosphere",     // dispatcher type — see below
  "vo": "Optional VO text...",     // synthesized via ElevenLabs, overlaid on visual
  "vo_audio": "assets/...mp3"      // OR: pre-recorded VO file (overrides vo)
}
```

If both `vo` (text) and `vo_audio` (file) are present, `vo_audio` wins.

### Scene type: `runway_atmosphere`

Text-to-video Runway clip. Used for hooks, transitions, problem visualization, B-roll where no source image exists.

```jsonc
{
  "id": "hook",
  "duration": 5,
  "type": "runway_atmosphere",
  "model": "veo3.1",              // optional; default veo3.1. Other: gen4.5, veo3.1_fast
  "prompt": "Cinematic close-up of...",
  "vo": "Optional VO over this clip"
}
```

**Constraints (see also `intro-trailer/references/runway-api-constraints.md`):**
- `veo3.1`: duration must be 8
- `veo3.1_fast`: 4, 6, or 8
- `gen4.5`: 5 only

The orchestrator rounds the requested duration to the nearest allowed value.

### Scene type: `runway_i2v`

Image-to-video. Used when you have a source photo (team, product, location) and want subtle motion.

```jsonc
{
  "id": "team-broll",
  "duration": 5,
  "type": "runway_i2v",
  "seedImage": "assets/team-photo.jpg",
  "prompt": "Slow camera push-in, subtle smiles, warm office lighting",
  "vo": "Built by people who get it"
}
```

**Seed image constraints:**
- File size < ~5MB after base64
- Aspect ratio ≥ 0.5 (not taller than 2:1 portrait)

### Scene type: `screenshot_kenburns`

Ken Burns motion on a still image. Cheapest scene type (no Runway call). Best for product screenshots, dashboards, lifestyle photos.

```jsonc
{
  "id": "dashboard",
  "duration": 8,
  "type": "screenshot_kenburns",
  "image": "assets/dashboard.png",
  "motion": "zoom_in",            // zoom_in | zoom_out | pan_right | pan_left | drift
  "vo": "Manage your customers in one place"
}
```

The image should be 1920×1080 or larger so the Ken Burns crop doesn't pixelate.

### Scene type: `logo_reveal`

ffmpeg-built logo scale-up animation. Logo starts small at center, grows to fill the screen over the scene duration.

```jsonc
{
  "id": "reveal",
  "duration": 6,
  "type": "logo_reveal",
  "vo": "Introducing ProductName"
}
```

Uses the `brand.logo` from the top-level brand config. The logo PNG should have a transparent background.

### Scene type: `cta_slide`

Designed CTA card with logo + headline + URL.

```jsonc
{
  "id": "cta",
  "duration": 8,
  "type": "cta_slide",
  "headline": "Try it free",
  "subhead": "14-day trial, no card",
  "ctaUrl": "example.com",
  "vo": "Visit example dot com today"
}
```

Background is a gradient using brand colors. Headline in Impact-style font, subhead in Helvetica.

### Scene type: `testimonial`

Quote card with optional customer photo.

```jsonc
{
  "id": "proof",
  "duration": 6,
  "type": "testimonial",
  "quote": "Saved us 10 hours every week.",
  "name": "Sarah Johnson, OpsLead at Acme",
  "photo": "assets/sarah.jpg",
  "vo": "Customers see results in week one"
}
```

Photo is rendered as a circular avatar on the left, quote and name on the right. If no photo, just centered text on a brand-color gradient.

### Scene type: `bumper` (planned)

Short branded interstitial (2-3s) with logo, color flash, and sting SFX.

### Scene type: `screen_recording` (planned)

Pre-recorded screen capture (e.g. Playwright + scripts). For when AI generation can't match the real app UI.

## Validation rules (enforced by orchestrator)

1. Sum of `scene.duration` should equal `duration` within ±2s
2. Every scene needs `id`, `duration`, `type`
3. `type` must be one of the dispatcher types
4. Runway scenes need `model` (default veo3.1 for t2v, gen4_turbo for i2v)
5. `runway_i2v` and `screenshot_kenburns` need their image to exist
6. Aspect ratios must be one of: 16:9, 9:16, 1:1, 4:5, 21:9

## Common patterns

### "Hook → Problem → Solution → CTA" (most commercials)

5 scenes, durations approximately: 4s + 8s + 30-40s + 8s.

### "Hook → 3 features → Proof → CTA" (product launches)

6-7 scenes: 4s + 3×8-10s + 6s + 10s.

### "Hook → Service → CTA" (local 30s ads)

3 scenes: 5s + 18s + 7s. Very tight, no fluff.

## Iteration workflow

1. Copy a template to `$PROJECT_DIR/brief/brief.json`
2. Fill in placeholders, add scene VO copy
3. `python3 make_commercial.py --only hook problem` to test the first few scenes
4. Review, edit VO copy, regenerate failed scenes
5. Once all scenes look right: `python3 make_commercial.py` for the full pass
6. Multi-aspect export happens automatically
