# ElevenLabs Voice Selection

Choosing the right voice is half of the commercial. The wrong voice makes a great script feel off-brand. Use this table to pick.

## The voice library (default ElevenLabs voices)

| Name | voice_id | Gender | Tone | Best for |
|---|---|---|---|---|
| Adam | `pNInz6obpgDQGcFmaJgB` | M | Deep, authoritative | SaaS, enterprise, financial services |
| Rachel | `21m00Tcm4TlvDq8ikWAM` | F | Warm, friendly, professional | Healthcare, wellness, services |
| Antoni | `ErXwobaYiN019PkySvjV` | M | Younger, upbeat, energetic | Local services, restaurants, retail |
| Domi | `AZnzlk1XvdvUeBnXmlld` | F | Soft, intimate, calm | Personal brand, therapy, lifestyle |
| Daniel | `onwK4e9ZLuTAKqWW03F9` | M | British, refined, polished | Luxury, premium brands |
| Bella | `EXAVITQu4vr4xnSDxMaL` | F | Sweet, conversational | Education, kids, food |
| Elli | `MF3mGyEYCl7XYWbV9V6O` | F | Emotional, expressive | Storytelling, documentary, charity |
| Josh | `TxGEqnHWrfWFTfGW9XjX` | M | Casual, friendly, podcast-style | Personal brand, indie products |
| Arnold | `VR6AewLTigWG4xSOukaG` | M | Strong, deep, narrator | Sports, action, dramatic |
| Sam | `yoZ06aMxZJJ28mfd3POQ` | M | Neutral, balanced | Generic narrator |
| Kevin Champlin | `q0IMILNRPxOgtBTS4taI` | M | Kevin's personal cloned voice | Champlin Enterprises projects, personal brand work |

## Decision rules

**Match the voice to the brand's customer:**
- Selling to enterprise IT? Adam (authoritative)
- Selling to consumers in a service business? Antoni (energetic)
- Selling to women's health? Rachel (warm)
- Selling to luxury market? Daniel (British)
- Selling to creators / indie founders? Josh (casual)

**Match the voice to the script's energy:**
- Calm, story-driven copy → Domi or Elli (intimate)
- Action-oriented "do this now" copy → Antoni or Arnold (urgent)
- Educational / informative copy → Rachel or Sam (neutral)
- Building drama with stakes → Adam or Arnold (deep narrator)

**Match the voice to the duration:**
- 30s ads → energetic voices (Antoni, Arnold) — short attention requires punch
- 60-90s commercials → narrator voices (Adam, Daniel, Rachel) — longer time tolerates calm
- 2+ minute pieces → conversational voices (Josh, Bella) — fatigue is a real concern

## Voice settings — stability and similarity_boost

`stability` (0.0-1.0):
- 0.30-0.45 — Maximum variability, emotive, can crack/sigh. Use for storytelling, emotional pieces.
- 0.50 — Balanced (default). Use for most commercials.
- 0.65-0.80 — Highly consistent, narrator-like. Use for explainers, training, podcasts.

`similarity_boost` (0.0-1.0):
- 0.50-0.70 — Allows the model to interpret intonation freely
- 0.75 — Default, balanced
- 0.85-0.95 — Tightly matches the voice's training samples. Use when the voice's signature matters (e.g. Kevin's cloned voice).

## Kevin's defaults (for Champlin Enterprises and personal projects)

- Personal brand / hire-me content → Kevin's cloned voice (`q0IMILNRPxOgtBTS4taI`) with high similarity_boost (0.90)
- Client SaaS demos → Adam (commercial narrator)
- Client local service ads → Antoni (energetic)
- Client luxury / premium → Daniel (British)
- Wellness / healthcare clients → Rachel (warm female)

## Pre-flight VO checklist

Before generating a full commercial:

1. Read your VO copy out loud — does it sound like the voice you picked?
2. Check pronunciation — Runway/ElevenLabs gets brand names wrong sometimes. Test single brand mentions first.
3. Verify the total VO duration fits the scene durations (rough: 145 words per minute average)
4. Plan for 1-2 VO re-takes per commercial (different stability, slightly edited copy)

## Cost ($0.30 per 1000 characters)

| Commercial length | Typical VO chars | VO cost |
|---|---|---|
| 30s ad | 600-800 | $0.20 |
| 60s ad | 1200-1500 | $0.42 |
| 90s ad | 1800-2200 | $0.60 |

Cheap. The Runway + ffmpeg work dominates the total cost.

## When NOT to use ElevenLabs

- The client is the talent (founder narrating their own product) — record real audio
- The voice needs regional accent / dialect not in the library — record real audio
- The brand has a signature voice actor — keep using them, don't AI-replace
- Legal requirement to disclose AI voice — varies by jurisdiction; the FTC has been hinting at requirements for AI VO

## Adding a custom cloned voice

If a client wants their own voice cloned:
1. Record 1-5 minutes of clean reference audio
2. Upload via ElevenLabs UI → Voice Lab → Instant Voice Clone (or Professional Voice Clone for paid tier)
3. Get the new voice_id
4. Update the project's brief: `voice.voice_id: "new-id-here"`, `voice.similarity_boost: 0.90`
