# Shot Prompt Templates

Copy-paste shot definitions for common beats. All in `gen4_turbo` i2v or `veo3.1` t2v unless noted.

## Atmosphere beats

### Hush (opening void)
```
Pitch-black empty arena stage at night. A single glowing orange ember drifts slowly
upward through pure black void. Faint volumetric haze in the air. Cinematic 35mm
anamorphic, shallow depth of field, very dark, almost imperceptible motion. No
people, no text, no logos.
```
Model: `veo3.1_fast`, duration 4s, t2v.

### Heaven cracks
```
Massive obsidian-black storm clouds split open from the center to reveal golden
god-rays piercing downward. A backlit angel silhouette with enormous outstretched
wings descends slowly through the opening. Volumetric light shafts, slow-moving
glowing dust particles, biblical atmosphere. Camera slowly tilts upward from
horizon. Cinematic, photo-real, epic, no text or logos.
```
Model: `veo3.1`, duration 8s, t2v.

### Hell rises (moderation-safe phrasing)
```
From the bottom of frame the earth cracks open with glowing molten orange and red
fissures. Black smoke columns rise rapidly. Massive underground forge erupts
upward, lava cascading, embers and sparks flying everywhere, intense heat haze
distortion. Towering shadowy silhouette of a horned warrior rises from the
inferno. Camera slowly pushes in. Photo-real, cinematic, dark fantasy, no text or
logos.
```
Model: `veo3.1`, duration 8s, t2v. Avoid "devil" — use "horned warrior" or "primal shadow figure."

### Collision (winged silhouettes)
```
Two opposing winged silhouettes — one radiant golden, one wreathed in fire and
smoke — collide head-on in mid-air over a fiery battlefield. A massive lightning
bolt strikes between them, blowing out the entire frame to brilliant white. End
on pure white flash. Cinematic, photo-real, no text or logos.
```
Model: `gen4.5`, duration 5s, t2v.

### Lightning + fire build (single shot, both elements together)
```
Massive lightning bolts crash down from a black thunder sky from the top of frame.
Simultaneously, walls of red and gold fire and flames rise up from the bottom of
the frame to meet the lightning, building together in chaos. Thick black smoke
columns, sparks and embers flying everywhere. No figures, no text, no logos.
Cinematic, photo-real, dark dramatic, building energy.
```
Model: `veo3.1`, duration 8s, t2v.

## Logo reveal beats

### Logo emerges from distance (depth push)
```
Through swirling walls of smoke and flickering lightning, the [BRAND] logo is
barely visible deep in the background, glowing faintly in molten gold and deep
red. The camera slowly pushes through the storm toward the logo, which grows
steadily larger as it approaches the center of frame, still partially obscured by
smoke. The logo shape stays exactly as shown. Cinematic, photo-real fire and
smoke.
```
Model: `gen4_turbo`, duration 5s, i2v, seed = on-black logo PNG.

### Logo BANG (impact moment)
```
The [BRAND] logo SLAMS into full size at center of frame on a massive impact
moment. A blinding white-hot flash radiates outward, fire bursts in all directions
from behind the logo in deep red and gold flames, thick smoke billows past,
lightning still crackling at the edges of frame. The logo glows brilliantly and
stays perfectly steady at center. Maximum drama, hero moment. The logo shape
stays exactly as shown. Cinematic, photo-real.
```
Model: `gen4_turbo`, duration 5s, i2v, seed = on-black logo PNG.

### Logo explosion + push forward (continues the BANG)
```
The [BRAND] logo at full size center frame explodes outward with flames and
lightning bolts in all directions. The logo itself is engulfed in red and gold
fire while remaining clearly visible. Camera pushes forward toward the logo as it
bursts. No dreamy clouds anywhere — only sharp fire, lightning, and smoke. The
logo shape stays exactly as shown. Cinematic, photo-real, explosive hero moment.
```
Model: `gen4_turbo`, duration 5s, i2v.

### Final logo stamp (energy held to end)
```
The [BRAND] logo glows at peak intensity in molten gold and deep red. Lightning
bolts crackle and arc around the edges of the logo. Roaring fire surges below the
logo in red, gold, and orange flames. Bright sparks and embers fly off the logo
letters in all directions. Heaven-light beams shoot up from behind. The logo
shape stays exactly as shown. Cinematic, photo-real, epic final hero moment.
```
Model: `gen4_turbo`, duration 5s, i2v.

## Cast reveal variations

### Standard push-in (default)
```
Slow cinematic push-in on the man in the frame. Subtle dramatic backlight,
drifting smoke around him, gentle stage-light flicker. He stands still and
intense. Keep his face and identity exactly as shown — do not change his
features. Concert film look, shallow depth of field.
```

### Push-in with motion (avoid "looks too static" feedback)
```
Cinematic push-in on the man in the frame. He slowly turns his head toward the
camera with intensity. His hair flows and shifts in a gentle wind. Smoke and
embers swirl actively around him. Blue and red stage lights flicker and pulse
dramatically from opposite sides. Keep his face and identity exactly as shown —
do not change his features. Concert film look, shallow depth of field, strong
dynamic motion, not a still photo.
```

### Low-angle hero shot (for lead guitarists)
```
Slow low-angle hero push-in on the man in the frame. Lens flare from a single
stage spotlight, soft volumetric haze. Keep his face and identity exactly as
shown — do not change his features. Concert film look, shallow depth of field.
```

### Rim-lit dramatic (for bassists)
```
Slow cinematic push-in on the man in the frame. Blue and red rim lighting from
opposite sides, thin smoke wisp drifting through. Keep his face and identity
exactly as shown — do not change his features. Concert film look, shallow depth
of field.
```

### Drum kit silhouette (for drummers)
```
Slow cinematic push-in on the man in the frame. Drum kit silhouette behind him
in deep shadow, drifting smoke, occasional ember floating up. Keep his face and
identity exactly as shown — do not change his features. Concert film look,
shallow depth of field.
```

## Crowd / event beats

### Standard crowd surge
```
Live concert crowd surge from behind the band's perspective. Hands raised,
jumping. Pyrotechnic plumes erupt from the stage in foreground. Stage lights
strobe. Camera floats forward over the crowd. High energy, photo-real, concert
film grain. Keep crowd composition recognizable.
```

### Charity event / signature event
```
Crowd at [EVENT_NAME] charity event surging with hands raised, fans cheering and
jumping. Pyrotechnic flashes erupt above the crowd, stage lights strobe in the
back. Camera floats forward over the crowd capturing the energy. High energy,
photo-real, concert film grain. Keep crowd composition recognizable.
```

## Group / band-assembled beats

### Full band on smoke-filled stage
```
The full band stands assembled on a smoke-filled stage. Fire trails roll across
the floor behind them, sparks falling from above. Camera pulls back slowly,
revealing the scale of the stage. Keep each member's identity exactly as shown —
do not change their faces. Cinematic, epic, photo-real.
```

## Style modifiers (suffixes you can append)

| Goal | Append |
|---|---|
| More grain / 35mm look | "Anamorphic lens flare, 35mm film grain, slight chromatic aberration." |
| Cooler palette | "Cool blue and teal lighting palette, low-key cinematography." |
| Warmer palette | "Warm amber and orange tungsten lighting palette." |
| Slower / dreamier | "Slow-motion 60fps captured feel, dreamy depth of field." |
| Faster / more aggressive | "Whip-pan camera motion, fast cuts, high-energy editing rhythm." |
| Less text risk | "No text, no logos, no signage anywhere in frame." |

The "no text or logos" suffix is especially important — Runway will sometimes hallucinate band names or text into a frame if not explicitly told not to.
