# The Hybrid Workflow — How Runway + ElevenLabs + ffmpeg Interact

This skill orchestrates three subsystems that don't natively know about each other. Understanding the data flow makes the rest of the skill make sense.

## The state machine

```
                                ┌────────────────┐
                                │   brief.json   │
                                └────────┬───────┘
                                         │
                                         ▼
                            ┌──────────────────────────┐
                            │   make_commercial.py     │
                            │   (orchestrator)         │
                            └────┬──────┬──────────────┘
                                 │      │
              ┌──────────────────┘      └──────────────────┐
              │                                            │
              ▼                                            ▼
      ┌──────────────┐                            ┌──────────────┐
      │   Runway     │                            │  ElevenLabs  │
      │   API        │                            │  API         │
      │              │                            │              │
      │ - t2v        │                            │ - TTS        │
      │ - i2v        │                            │ - SFX        │
      │ - image gen  │                            │              │
      └──────┬───────┘                            └──────┬───────┘
             │                                            │
             ▼                                            ▼
      .mp4 clips                                     .mp3 VO files
             │                                            │
             └──────────────────┬─────────────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   ffmpeg         │
                       │   composer       │
                       │                  │
                       │ - per-scene comp │
                       │ - concat         │
                       │ - music mix      │
                       │ - aspect crop    │
                       └────────┬─────────┘
                                │
                                ▼
                       commercial-16x9.mp4
                       commercial-9x16.mp4
                       commercial-1x1.mp4
```

## Per-scene processing

For each scene in `brief.scenes`:

1. **Dispatch by `type`** — orchestrator picks the right generator/builder
2. **Generate visual** — Runway API OR ffmpeg ImageMagick (depending on type)
3. **Generate VO** (if scene has `vo`) — ElevenLabs API → MP3
4. **Compose scene** — ffmpeg merges visual + VO, trims to scene duration
5. **Save final per-scene MP4** → `generated/scenes/{id}-final.mp4`

After all scenes are processed, the concat + music + aspect pass runs.

## Why this architecture (vs. alternatives)

**Alternative 1: Use social-video for everything.**
- social-video doesn't do Runway generative video. Adding it means duplicating Runway code or invoking a separate process.
- Output formats are different (social-video is reel-focused, this skill needs commercial pacing).

**Alternative 2: Pure Runway everything (including TTS via Runway's ElevenLabs proxy).**
- Runway's ElevenLabs proxy works but the voice library is less obvious; direct ElevenLabs API is simpler.
- Composing video + audio at the API level is more friction than just calling ffmpeg.

**This architecture:**
- Each subsystem does one job well (Runway: AI video. ElevenLabs: VO. ffmpeg: composite.)
- Easy to swap any one (e.g. replace Runway with Pika or Sora when those become better)
- Standard ffmpeg means standard debugging — no black box

## State per project

The orchestrator writes intermediates to `$PROJECT_DIR/generated/`:

```
generated/
├── runway/{scene_id}.mp4    # raw Runway output
├── vo/{scene_id}.mp3        # ElevenLabs VO
├── music/bed.mp3            # music bed (sourced or generated)
├── overlays/                # PNG overlays for ffmpeg (CTA, lower-thirds)
└── scenes/{scene_id}-final.mp4  # composed scene (visual + VO + trim)
```

The orchestrator is **resumable**: it checks if intermediates exist and skips regenerating. To re-do a specific scene:

```bash
# Delete the scene's intermediates
rm generated/{runway,vo,scenes}/hook*

# Re-run only that scene
python3 make_commercial.py --only hook
```

The final concat + aspect-export pass always runs.

## VO synthesis details

ElevenLabs API direct call (no Runway proxy):

```python
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
xi-api-key: ${ELEVENLABS_API_KEY}
Content-Type: application/json
Accept: audio/mpeg

{
  "text": "Your VO text here.",
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75
  }
}
```

Returns audio/mpeg bytes — save directly to file.

`ELEVENLABS_API_KEY` is in `~/.zshrc` and exported to env. The orchestrator reads from env. If env var is missing, the orchestrator exits with an error.

## Runway API details

Same patterns as the `intro-trailer` skill — see `~/.claude/skills/intro-trailer/references/runway-api-constraints.md` for the full catalog of duration/ratio/moderation constraints.

Key reminders:
- Required: `X-Runway-Version: 2024-11-06` header
- Credit balance is at `dev.runwayml.com/billing` (separate from app.runwayml.com)
- gen4_turbo durations must be 5 or 10
- veo3.1 duration must be 8

## ffmpeg pipeline

The composite pipeline (per scene + final):

**Per-scene composition:**
```
visual.mp4 (silent) + vo.mp3 → ffmpeg → scene-final.mp4 (visual + VO audio, trimmed to scene duration)
```

**Final concat:**
```
[scene-01.mp4, scene-02.mp4, ...] → ffmpeg -f concat → intermediate.mp4
intermediate.mp4 → ffmpeg scale+crop to aspect → commercial-{aspect}.mp4
commercial-{aspect}.mp4 + music_bed.mp3 → ffmpeg amix → final commercial-{aspect}.mp4
```

The music mix uses `amix` with the `volume` filter for VO ducking (~0.4× during VO).

**Aspect crop strategy:** the orchestrator scales each scene to "increase" mode then crops to the target aspect. This means the SOURCE aspect (16:9 from Runway) gets center-cropped when fitting to 9:16. For better vertical handling, consider:
- Setting a per-scene `cropFocus: {x: 0.5, y: 0.4}` to bias the crop center
- Or pre-rendering some scenes in vertical Runway ratios (`720:1280`) for the 9:16 master

Future enhancement: smart-crop using face/saliency detection.

## Iteration tips

1. **Build scene-by-scene first** — `--only hook` to test the opener, then `--only hook problem` to add the next, etc.
2. **VO is cheaper than Runway** — iterate VO copy multiple times before re-firing Runway clips
3. **Aspect ratio comes last** — perfect the 16:9 master, then render 9:16/1:1 from it
4. **Music bed last too** — too easy to over-tune music against a non-final cut

## When to call this skill vs sub-tools directly

**Call this skill:**
- Brief is a structured commercial with VO + scenes + CTA
- Multiple aspect ratios needed
- Client deliverable (not a personal experiment)

**Call sub-tools directly:**
- Just need a single Runway clip → use `intro-trailer` generate.py or curl
- Just need a VO snippet → curl ElevenLabs directly
- Just need to composite existing clips → ffmpeg directly

The skill is for when you need the WHOLE pipeline. For one-off pieces, the sub-tools are lighter.
