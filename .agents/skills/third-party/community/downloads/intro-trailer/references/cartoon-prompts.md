# Cartoon Character Generation

How to generate heaven-and-hell cartoon versions of real cast members that actually look like them and are the correct gender.

## The two biggest failure modes

1. **Wrong gender** — long-haired men render as women without explicit "MALE" language
2. **Wrong age** — older photos can render the subject as 20 years older than they are

Both fail because the image gen model latches onto secondary features (hair length, hair color, lighting) and infers wrong primary features (gender, age).

## The working prompt template

```
Stylized comic-book cartoon illustration of the MALE rock musician in the reference photo,
drawn as a rugged adult MAN — masculine features, square jaw, visible beard stubble or beard,
broad shoulders, rock-and-roll attire — as an {ANGEL|DEMON} character
with {halo_or_horns_details}.
Keep the man's facial likeness, hairstyle, and beard clearly recognizable.
DO NOT render as a woman or feminine character. He is a male rock band member.
Dark dramatic illustration art style with bold lines, vivid colors, dramatic shading.
Full character visible from chest up, facing camera. No text, no logos.
```

Five things the prompt does:
1. Capitalized **MALE** to emphasize gender
2. "rugged adult MAN" + specific masculine features
3. Explicit anti-prompt: "DO NOT render as a woman"
4. Specifies likeness preservation
5. Locks framing (chest up, facing camera) so all 6 cartoons match

## Angel vs Devil detail strings

**Angel:**
```
glowing golden halo above the head, large feathered angel wings extending behind,
heavenly golden god-rays and soft white smoke in the background
```

**Devil:**
```
curved red devil horns on the head, sharp pointed devil tail,
red and orange flames flickering behind, dark smoke and embers in the background
```

## Reference image requirements

For best likeness:
- **Frontal face shot** — three-quarter is OK, side profile rarely works
- **Clear lighting** — avoid stage shadows over half the face
- **Single subject** — group photos confuse the model
- **Recognizable hair / beard** — these are the model's anchor points for likeness
- **Resolution** — 512px on the shortest edge minimum, 1024px ideal

Pre-process recipe for typical phone screenshots (which fail Runway's `width/height ≥ 0.5` check):

```bash
magick screenshot.png \
  -crop 700x900+250+700 +repage \   # crop to just the subject
  -resize 832x \                    # resize to ≤ 1024 wide
  -quality 92 \
  members/subject-role.jpg
```

For taller-than-2:1 portraits, either crop to square-ish or pad with black:

```bash
magick portrait.jpg -gravity center -background black -extent 1024x1792 padded.jpg
```

## Three-three split assignments

Default angel/devil distribution for a 6-member band, alternating by stage role:

| Role | Side | Rationale |
|---|---|---|
| Vocals | Angel | Lead voice = "heavenly voice" archetype |
| Rhythm guitar | Devil | Counterpoint to vocals |
| Lead/rhythm guitar | Angel | |
| Lead guitar | Devil | Lead-guitar shred = devil archetype |
| Bass | Angel | Holds the rhythm together |
| Drums | Devil | Drummers always get the devil treatment |

This gives a balanced 3-3 split. Tweak based on the band's personality — some bands lean angel, some lean devil.

## Iteration workflow

If a generated cartoon doesn't match well:

1. **Wrong gender** — verify prompt has all the "MALE" emphasizers. Try a different reference photo with clearer masculine features (beard more visible, less feminine hair styling).

2. **Wrong age** — usually fixable with a newer reference photo. Add "young adult" or "mid-30s" if the person looks younger than the model is rendering them.

3. **Generic likeness** — the model is using the reference but rendering a generic person. Try a tighter crop on the face (less body, more facial detail). Or try a different image gen model: `gpt_image_2` and `gemini_image3_pro` handle likeness differently.

4. **Pose is wrong** — adjust "Full character visible from chest up" to be more specific: "front-facing portrait composition with shoulders square to camera".

5. **Style is wrong** — adjust the art style descriptor. "Dark dramatic illustration art style" gives bold lines + vivid colors. Alternatives:
   - "Gritty oil painting style, painterly brushwork" — more sophisticated
   - "Saturday-morning cartoon style, simple shapes, bright colors" — lighter tone
   - "Anime-influenced manga style, sharp lines, dramatic perspective" — Eastern aesthetic

## Cartoon flash placement in the timeline

A 1.5-second flash inserted AFTER each real-member reveal works best:

```
Real Paul reveal (5s)
→ Cartoon Paul flash (1.5s)
→ Real Rick reveal (5s)
→ Cartoon Rick flash (1.5s)
→ ...
```

Why after, not before:
- The audience sees the real face first (clear identity)
- Then the cartoon as a stylized reinforcement
- The cartoon doesn't "introduce" the wrong-looking version

Composite: 0.3s xfade in and out. Tighter than member→member because the cartoon is a flash, not a beat.

## Animation for cartoon flashes

Each cartoon PNG becomes a brief image-to-video clip:

```json
{
  "id": "06c",
  "duration": 1.5,                    // composite display duration
  "runwayDuration": 5,                // gen4_turbo minimum
  "mode": "image_to_video",
  "model": "gen4_turbo",
  "ratio": "1280:720",
  "seedImage": "cartoons/06c.png",
  "promptText": "Slow zoom forward into the cartoon character, with slight motion of wings/flames in the background, embers drifting. Keep the cartoon style and likeness exactly as shown."
}
```

`composite_seamless.py` reads `duration` for the `-t` trim, `generate.py` reads `runwayDuration || duration` for the API submit. The 5s clip gets trimmed to 1.5s in composite.

## Cost notes

- 6 cartoon images via `gen4_image`: ~60 credits total
- 6 cartoon animations via `gen4_turbo`: ~150 credits total
- Single cartoon iteration: ~35 credits (image + animation)
- Plan for at least one iteration round (likely Shawn/Aiden-style "doesn't look like him" or "looks female") → budget ~250 credits for the full cartoon system

## Skip cartoons entirely if:

- Client is conservative / not into the heaven-hell theme
- Cast members are public figures whose likeness matters more than stylization
- Budget is tight — cartoons add ~210 credits ($2–3) on top of the base trailer
- Iteration time is short — cartoons add a round of feedback

The trailer reads strong without cartoons. They're flavor, not foundation.
