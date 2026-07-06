# Runway ML API Constraints

Every constraint here was hit during the 303 build. Reading this before coding will save 30 minutes of cryptic 400 errors.

## API Base + Headers

```
POST https://api.dev.runwayml.com/v1/{endpoint}

Authorization: Bearer ${RUNWAY_API_KEY}
X-Runway-Version: 2024-11-06   # required, or the call fails
Content-Type: application/json
```

`X-Runway-Version` is mandatory. Omit it and every call returns a validation error with no hint about the missing header.

## Endpoints we use

| Endpoint | Purpose |
|---|---|
| `GET /v1/organization` | Probe auth + check credit balance + list available models |
| `POST /v1/image_to_video` | Animate a still image with a prompt |
| `POST /v1/text_to_video` | Generate video from prompt only |
| `POST /v1/text_to_image` | Generate still image, optionally with reference images |
| `GET /v1/tasks/{id}` | Poll generation status (`RUNNING` → `SUCCEEDED` / `FAILED` / `CANCELLED`) |

## Auth probe (cheapest sanity check)

```bash
curl -sS \
  -H "Authorization: Bearer ${RUNWAY_API_KEY}" \
  -H "X-Runway-Version: 2024-11-06" \
  https://api.dev.runwayml.com/v1/organization \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('credits:', d.get('creditBalance')); print('models:', sorted(d.get('tier',{}).get('models',{}).keys()))"
```

Returns 200 even with zero credits — credits gate generation, not auth. **Always check `creditBalance` before starting a multi-shot run.**

## Billing trap

`api.dev.runwayml.com` is billed **separately** from `app.runwayml.com`. An active Runway subscription does NOT fund API calls. Credits must be loaded at `dev.runwayml.com/billing`. First-time API users will get HTTP 402 on every generation despite paying for the consumer app.

## Video gen — duration constraints (model-by-model)

This is the single biggest source of validation errors. Each model accepts only specific durations:

| Model | i2v supported | t2v supported | Allowed durations |
|---|:-:|:-:|---|
| `gen3a_turbo` | ✓ | ✓ | 5, 10 |
| `gen4_turbo` | ✓ | ✗ | 5, 10 |
| `gen4.5` | ✗ | ✓ | 5 |
| `gen4_aleph` | ✓ | ✓ | varies |
| `veo3` | ✓ | ✓ | 8 |
| `veo3.1` | ✓ | ✓ | 8 |
| `veo3.1_fast` | ✓ | ✓ | 4, 6, 8 |
| `kling2.5_turbo_pro` | varies | varies | check API response |
| `kling3.0_pro` | varies | varies | check API response |
| `seedance2` | ✓ | ✓ | check API response |

**Gotcha:** `gen4_turbo` does NOT support text-to-video — only image-to-video. Use `gen4.5` for t2v gen4-style.

**Workaround for arbitrary durations** (e.g. cartoon flash @ 1.5s): submit at the model's minimum (5s for gen4_turbo), then trim to the display duration in ffmpeg with `-t 1.5`. The `prompts.json` schema in this skill supports a `runwayDuration` field for this — `composite.py` reads `duration` for the trim, `generate.py` reads `runwayDuration || duration` for the API submit.

## Video gen — ratio constraints

Each model accepts a specific enum of ratios. The error message will list the allowed values:

**gen4_turbo allowed ratios:**
`1280:720` (16:9), `720:1280` (9:16), `1104:832` (4:3), `832:1104` (3:4), `960:960` (1:1), `1584:672` (21:9)

**`1920:1080` is NOT allowed** for any model — Runway generates at lower resolution, you upscale to 1080p in post via the composite pipeline.

## Image gen — reference image constraints

Both ratio and file-size constraints apply to reference images passed as `referenceImages: [{uri: data_url}]`:

- **Aspect ratio:** width/height ≥ 0.5 AND ≤ 2.0. iPhone portrait screenshots at 1242×2688 (ratio 0.462) fail. Pad to make wider or crop to make squarer.
- **Base64 size:** the data URI must be ≤ ~5MB after base64 encoding. Raw file ≤ ~3.9MB safe upper bound. Resize large PNGs to JPG @ ≤ 1024px wide.
- **Format:** JPG, PNG, WebP all work. Uppercase `.PNG` extension is accepted.
- **Number of refs:** typically 1, may support 2–3 for some models — check error message.

Pre-process recipe:

```bash
# Resize + JPG-ify if file is too big
magick big.png -resize 1024x -quality 90 -strip /tmp/small.jpg

# Pad if portrait is too tall
magick tall-portrait.jpg -gravity center -background black -extent 1024x1792 /tmp/padded.jpg

# Get current dimensions to check ratio
magick identify /path/to/image
```

## Content moderation gotchas

Runway's third-party moderation hits common trailer language:

| Word | Result | Workaround |
|---|---|---|
| `devil` | Often flagged on `veo3.1` | `horned warrior silhouette`, `primal shadow figure`, `infernal demon` (sometimes ok) |
| `blood`, `gore` | Flagged | Just drop these |
| `nude`, `sexy` | Always flagged | Obviously avoid |
| Real celebrity names | Flagged | Use generic descriptors |
| Trademarked logos | Sometimes flagged | Caption the brief without naming brands |

When moderation hits, the response is:
```json
{
  "status": "FAILED",
  "failure": {
    "code": "42237218",
    "reason": "This request was rejected by the third party moderation service."
  }
}
```

Reword the prompt and resubmit. The same request body that worked yesterday can fail today as moderation rules update.

## Polling pattern

```python
delay = 5
while True:
    info = http_get(f"/v1/tasks/{task_id}")
    status = info["status"]
    if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
        break
    time.sleep(delay)
    delay = min(delay + 5, 30)  # backoff to 30s max
```

Generation times vary by model:
- `gen4_turbo` 5s clip: ~30–60 sec
- `veo3.1` 8s clip: ~60–120 sec
- `gen4_image`: ~15–30 sec
- `veo3.1` longer or complex: occasionally 3+ minutes

Don't poll faster than 5s — the API will throttle.

## Failure-as-output handling

`generate.py` in this skill is resilient: per-shot exceptions caught, logged, moves on to the next shot, reports failures at the end. Critical for batches of 20+ — without this, one moderation hit kills the whole run.

## Cost rough-pricing (subject to change — always verify)

| Model | Duration | Approx credits |
|---|---|---|
| `gen3a_turbo` 5s | 5s | ~25 |
| `gen4_turbo` 5s i2v | 5s | ~25 |
| `gen4_turbo` 10s i2v | 10s | ~50 |
| `gen4.5` 5s t2v | 5s | ~25 |
| `veo3.1` 8s t2v | 8s | ~75 |
| `veo3.1_fast` 8s t2v | 8s | ~30 |
| `gen4_image` (text-to-image) | — | ~10 |

Treat these as estimates — Runway adjusts pricing. Check actual cost via the org probe before/after a run.

## Tier limits (default API account)

From the `/v1/organization` response:
- `maxMonthlyCreditSpend`: 10000 (default)
- Per-model concurrency: 1–2
- Per-model daily generations: 50–200

A typical 130s trailer build uses ~1000 credits + iteration buffer (~500). One full client trailer fits comfortably in the monthly cap. Don't try to run 10 client trailers in one day — the daily cap will throttle you.
