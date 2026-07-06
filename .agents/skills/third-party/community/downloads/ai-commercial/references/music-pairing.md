# Music Style → Commercial Type Pairing

Music sells. The wrong music kills a great script. Pick by audience, not by what you like.

## The 5 styles + when to use each

### `cinematic`
- **Feel:** Low strings, building tension, drop at the CTA
- **Tempo:** 60-80 BPM, builds to 100 BPM at climax
- **Use for:** SaaS, enterprise, financial services, product launches, anything where "this is a big deal" matters
- **Avoid:** Cheap services, food, lifestyle (too dramatic)

### `upbeat`
- **Feel:** Drums + bass, high tempo, encourages immediate action
- **Tempo:** 110-130 BPM, consistent energy throughout
- **Use for:** Local service ads, restaurants, retail, fitness, gyms, food delivery
- **Avoid:** Luxury, healthcare, somber topics (feels too aggressive)

### `ambient`
- **Feel:** Soft pads, gentle motion, doesn't compete with VO
- **Tempo:** 50-70 BPM, ethereal
- **Use for:** Personal brand intros, healthcare, wellness, therapy, education
- **Avoid:** Action ads, calls-to-action (too soft to drive urgency)

### `electronic`
- **Feel:** Synths, modern pulse, contemporary feel
- **Tempo:** 100-120 BPM
- **Use for:** Tech products, agencies, creative services, fashion, modern brands
- **Avoid:** Traditional businesses, legal, financial (feels too "cool")

### `acoustic`
- **Feel:** Guitar, organic instruments, warm
- **Tempo:** 70-100 BPM
- **Use for:** Wellness, lifestyle, family brands, restaurants (especially cafes), travel, charity
- **Avoid:** Tech, urban, action-driven ads (feels out of place)

## Decision tree

```
Selling to businesses (B2B)?
├── Enterprise / authoritative → cinematic
├── Modern / tech-forward → electronic
└── Creative / agency → electronic OR cinematic

Selling to consumers (B2C)?
├── Action needed now (call/order/book) → upbeat
├── Lifestyle / aspirational → acoustic OR ambient
├── Health / wellness → ambient
├── Luxury / premium → cinematic OR none-with-VO-only
└── Entertainment / fun → upbeat
```

## Volume guidance

`music.volume` field in the brief, range 0.0-1.0:

- **0.15-0.20** — Very background, almost subliminal. Use when VO is dense and critical (training, instructions).
- **0.22-0.28** — Standard commercial level. Music supports the VO without competing.
- **0.30-0.35** — Music has presence, "feels" more. Use for hype/launch ads.
- **0.40+** — Music is a co-star. Only use when VO is sparse or when there's a music-driven moment (logo reveal, dramatic pause).

The orchestrator automatically ducks music to ~0.4× the configured volume DURING VO segments — so if `music.volume: 0.28`, during VO it drops to ~0.11. This keeps the VO clear without losing music presence in silent gaps.

## Music bed generation

The skill auto-generates the music bed when running `make_commercial.py` — no manual step required. It calls `scripts/generate_music.py` (which imports social-video's NumPy synth function), produces a WAV the length of the full commercial + 4s tail, and converts to MP3 at 192kbps.

Manual override:

```bash
# Override the auto-gen by dropping a custom track first
cp /path/to/licensed-track.mp3 $PROJECT_DIR/generated/music/bed.mp3
python3 ~/.claude/skills/ai-commercial/scripts/make_commercial.py
# Orchestrator sees existing bed and skips auto-gen
```

Or generate manually with different style:

```bash
PROJECT_DIR=~/clientx-commercial python3 ~/.claude/skills/ai-commercial/scripts/generate_music.py \
  --style ambient --duration 60 --force
```

### Styles currently implemented in the underlying synth

- **cinematic** — full implementation. Build / impact / drop / resolution with strings, drones, kicks, hats, lead melody, timpani.
- **ambient** — full implementation. Slow pads, gentle motion, minimal percussion.

### Styles that fall back to cinematic (until upstream adds them)

- **upbeat** — currently falls back to cinematic. Future: add drum-bass-driven pattern.
- **electronic** — fallback. Future: synth arpeggios + 4-on-the-floor.
- **acoustic** — fallback. Future: guitar pluck + warm pad.

When social-video adds these styles, this skill picks them up automatically (loaded dynamically from social-video's `generate_music`).

### Royalty-free or custom override

For premium clients or specific brand sounds:
- Epidemic Sound / Artlist / YouTube Audio Library — drop the MP3 in `$PROJECT_DIR/generated/music/bed.mp3` before running
- Suno / Udio AI-generated music — same drop-in pattern, verify license terms allow client use

## Common mistakes

- **Music too loud** — VO gets buried. Always render a test at the configured volume and re-listen on phone speakers (where most viewers will watch).
- **Music genre clash with VO voice** — calm narrator over upbeat electronic feels schizophrenic. Match energy levels.
- **No music drop at the CTA** — a small swell or pause at the CTA helps it land. Future feature in the orchestrator.
- **Same music every commercial** — clients notice. Have 2-3 beds per style on rotation.

## Track recommendations (royalty-free starting points)

For each style, here are starter tracks that work well at 25% volume:

- **Cinematic** — "Tomorrow" by Bensound, "Cinematic Documentary" by Lesfm
- **Upbeat** — "Buddy" by Bensound, "Sun" by Lesfm, "Snowfall" tempo
- **Ambient** — "Slow Motion" by Bensound, "Background" by Lesfm
- **Electronic** — "Sci-Fi" by Bensound, "The Lounge" by Lesfm
- **Acoustic** — "Acoustic Breeze" by Bensound, "Sunny" by Lesfm

These are public-license freebies — verify license terms before client use.
