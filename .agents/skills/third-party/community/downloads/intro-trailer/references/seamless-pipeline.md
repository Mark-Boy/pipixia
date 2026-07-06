# The Seamless-Composite Pipeline

How to make 20+ separately-generated Runway clips feel like one continuous film.

## The diagnosis

Each Runway clip is generated independently — different models, different lighting, different motion energy, different grain. Even with crossfades, the eye registers stitched cuts because:

1. **Color mismatch** — some clips warm, some neutral, some cool
2. **Grain mismatch** — Veo and gen4_turbo render at different sharpness/noise levels
3. **Motion energy mismatch** — atmosphere shots are chaotic, member portraits are slow
4. **No through-line element** — nothing visually carries from one shot to the next

Crossfading hides hard cuts but cannot fix the underlying inconsistency. You need finishing passes that unify ALL the clips uniformly.

## The four-part finishing pass

Applied to every clip in `composite_seamless.py`. Skip any one and the seams reappear.

### 1. Unified cinematic color grade

ffmpeg filter chain applied to every clip:

```
eq=contrast=1.12:saturation=1.08:brightness=-0.01,
colorbalance=rs=0.08:gs=-0.02:bs=-0.08:rm=0.04:gm=-0.01:bm=-0.04,
curves=master='0/0 0.08/0.04 0.92/0.96 1/1',
noise=alls=4:allf=t
```

Breakdown:
- `eq` — +12% contrast, +8% saturation, slight darken (-0.01 brightness)
- `colorbalance` — shadows warmer (R+, G-, B-), midtones slightly warmer
- `curves` — crushes blacks (0.08 input → 0.04 output) and lifts highlights (0.92 → 0.96)
- `noise=alls=4:allf=t` — subtle temporal film grain on luma

For a different mood (cool atmosphere instead of warm fire):
- Cooler: `colorbalance=rs=-0.05:bs=0.08` (cool shadows, warm highlights would be `colorbalance=rs=0.05:bs=-0.05` etc.)
- Pastel/dreamy: `eq=contrast=0.9:saturation=1.2`
- High contrast B&W moments: `eq=saturation=0` on specific clips only

### 2. Persistent ember/smoke overlay layer

**Single biggest unifier.** A slow-drifting transparent ember layer running underneath every shot at ~12% opacity.

Generate it once:

```bash
python3 scripts/build_ember_overlay.py
```

This fires a Runway veo3.1 t2v request with the prompt:
> "Slow drifting glowing orange, gold, and amber embers floating upward and gently sideways across the entire frame. Thin tendrils of dark smoke wisping and curling slowly. Pure jet-black background, no other elements, no figures, no text, no logos. Volumetric particle effect, atmospheric, dreamy slow motion, deep contrast between the bright glowing embers and the pitch black space."

Output: `overlays-source/embers-veo31-8s.mp4` (~10MB, ~75 credits).

Loop it via ffmpeg `-stream_loop -1` over every clip:

```
[ember:v]scale=1920:1080,setsar=1,fps=24,format=rgba,colorchannelmixer=aa=0.12[em];
[base][em]overlay=0:0:shortest=1[base2]
```

The `colorchannelmixer=aa=0.12` sets alpha to 12% so embers are visible but never overwhelm. Tune up to 15% for more presence, down to 8% for subtlety.

**Why this works:** Even member portraits get gentle embers floating through. The same particle layer is present in the heaven shot, the logo bang, AND the cast reveals — so all the shots feel like they exist in the same physical space.

### 3. Soft radial vignette

Pre-rendered PNG with ImageMagick:

```bash
magick -size 1920x1080 radial-gradient:'rgba(0,0,0,0)-rgba(0,0,0,0.55)' vignette.png
```

Composited on every clip with `overlay=0:0`. The transparent center keeps the subject bright; the 55% black corners darken the edges, drawing the eye inward.

**For different moods:**
- Stronger vignette (more cinema): bump from `0.55` to `0.7`
- Subtle (more documentary): drop to `0.35`
- None: skip this step

### 4. Light film grain

The `noise=alls=4:allf=t` in step 1 handles this — `t` flag means temporal (different per frame), giving a subtle film-grain shimmer. Strength 4 is barely-perceptible-but-present.

For grittier rock-and-roll feel: bump to `alls=8`. For clean cinema: drop to `alls=2`. For "broadcast safe": skip entirely.

## Variable crossfade durations (not 0.5s on every cut)

Uniform crossfades give an unnatural rhythm. Different beats need different transition lengths:

| Junction type | Crossfade | Reasoning |
|---|---|---|
| Atmosphere → atmosphere | 0.7–0.8s | Dreamy, gives time to absorb |
| Atmosphere → action (collision flash) | 0.2s | Near-hard, the flash IS the transition |
| Action → logo BANG | 0.1s (hard cut) | Maximum impact |
| Logo → member reveal | 0.5–0.6s | Cinematic but clear |
| Member → member | 0.4s | Tight, identity-forward |
| Member → cartoon flash | 0.3s | Stylistic insert |
| Cartoon → next member | 0.3s | Same |
| Member final → photo collage | 0.5s | Wide-canvas transition |
| Collage → event beat | 0.6s | Same |
| Event → group assembled | 0.6s | Same |
| Group → final logo | 0.5–0.6s | Building to close |

Implementation: a dict mapping `(from_id, to_id) -> seconds` in `composite_seamless.py`. The xfade chain is built by computing cumulative offsets:

```python
cum_offset = 0.0
for i in range(1, len(shots)):
    xf = XFADE.get((shots[i-1]["id"], shots[i]["id"]), 0.5)
    if i == 1:
        cum_offset = shots[i-1]["duration"] - xf
    else:
        cum_offset += shots[i-1]["duration"] - xf
    # ... emit "prev_label INPUT_i xfade=duration=xf:offset=cum_offset out_label"
```

## Why this isn't done at generation time

You could try to bake the grade and ember layer into the prompt for every Runway shot, but it fails:
- Prompts are interpreted differently per model (gen4_turbo vs veo3.1 read "moody embers" differently)
- Member reveal shots can't have ember floating through without the model also putting embers in the wrong place
- You lose deterministic control — every iteration of a shot will have slightly different embers/grade

Better: generate the shots with **clean, simple prompts** focused on the content (member, atmosphere, logo). Apply the finishing pass uniformly in post. Every iteration of a single shot will composite identically.

## Tagline overlay handling

The final shot gets a `tagline_card.png` composited with fade-in starting at 1.0s of the clip:

```
[tagline:v]format=rgba,fade=in:st=1.0:d=0.5:alpha=1[tc];
[base][tc]overlay=0:0:shortest=1[v]
```

The `tagline_card.png` is rendered by `render_overlays.sh` using ImageMagick (because most Homebrew ffmpeg builds lack `drawtext` — no freetype). Font is Futura Bold with letterspacing 8 for the tagline, with a 3px-offset shadow underneath for contrast against bright backgrounds.

## Re-running iterations

If you change a shot or the XFADE config:

```bash
# Clean tmp intermediates
rm -rf output/tmp

# Re-composite
python3 scripts/composite_seamless.py
```

The composite is fast (~3–5 min for 130s output) because most time is the per-clip color grade pass. If you only changed a few clips, you could implement smart caching — but the full re-run is cheap enough that caching adds complexity for little gain.

## Output specs

- H.264: CRF 18, slow preset, yuv420p, no audio — universally playable, ~80–150 MB for 130s
- ProRes HQ: profile 3 (HQ), no audio — for venue rigs, AVID, Premiere, FCP edits, ~1.5–2 GB
- Both at 1920×1080 @ 24fps

24fps is cinematic and 23.976 has DCP/film convention but standard 24 is fine for venue playback. Don't ship at 30fps — defeats the "cinema" feel.
