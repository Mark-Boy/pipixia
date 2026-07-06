# Design Tokens — a portable starter system

Every premium UI starts from explicit tokens, not ad-hoc values. This is a portable reference for building a color + surface + spacing token system in OKLCH and wiring it into Tailwind v4. Adapt the names to your stack (CSS variables / Tailwind theme / framework theme objects) but keep the **scale** — the lightness array and the elevation ladder are the durable parts.

---

## Color foundation: OKLCH

Build color in **OKLCH**, not HEX/HSL. `oklch(L C H)` expresses color as **L** (lightness 0–1), **C** (chroma, 0 to ~0.37 in the P3 gamut), and **H** (hue 0–360). Default to it on any new Tailwind-v4 project. Why it beats HSL/hex math:

- **Perceptual uniformity** — one lightness value looks equally bright across every hue, so generating a consistent 50→950 ramp is trivial and reliable. (HSL is not perceptually uniform: `hsl(220 100% 50%)` and `hsl(60 100% 50%)` share a "lightness" number but look wildly different in brightness.)
- **No hue shift** — your blue stays blue from 50 to 950 instead of drifting purple, which is exactly what naive HSL `lighten()`/`darken()` math does.
- **Wide gamut (P3 / Rec.2020)** — more vivid colors on modern displays, future-proof.
- **Smoother gradients** — interpolating in OKLCH skips the muddy gray middle.

Tailwind v4 ships its entire palette in OKLCH for these reasons. OKLCH was introduced by Björn Ottosson (Dec 2020).

### The ramp recipe

Fix a per-step **lightness** array (this one matches Tailwind's feel), then pick a **chroma** that has no gaps across the hue spectrum at each step, holding the hue roughly constant:

```
L = [97.8, 93.6, 88.1, 82.7, 74.2, 64.8, 57.3, 46.9, 39.4, 32, 23.8]%   /* 50 → 950 */
```

- **Reduce chroma at the extremes** (50 and 950) so the lightest and darkest shades don't look radioactive.
- **Pro touch:** a ~20–30° hue shift toward warm/cool at the ends adds depth (e.g. neutrals warm slightly toward the shadows).
- Choose the base shade (≈500) as "a color that would work well as a button background," then build up and down from it.
- Generators: oklch.com, the Tailwind v4 palette generators, Coolors, Atmos, ColorBox.

This recipe (the Evil Martians approach) is what makes a full 10-shade ramp reliable: lock lightness, solve for chroma, keep hue steady. **Swap one hue number and the whole ramp stays balanced** — that's how you make a palette yours in a single number.

### Neutrals

- **Never pure black (#000) or pure white (#fff) for large areas.** Pure black on white is 21:1 — harsh, causes haloing/eye strain, and reads cheap. Use a near-black (a very dark desaturated value, e.g. something around `#0a0a0a`) and an off-white (e.g. something around `#fafafa`) as your endpoints.
- **Tint your grays** slightly toward the brand hue (cool grays lean blue, warm grays lean red/yellow) for a cohesive, premium feel. Pure grayscale "doesn't exist in nature" and can read unnatural.
- **Temperature is a brand decision.** Warm neutrals feel human/editorial; cool neutrals feel technical/corporate.

---

## Example: a ready-to-use OKLCH `@theme` block

Drop this in as a starting point. It's a warm off-white/near-black neutral ramp, a confident teal-leaning **primary** (instead of the default indigo/purple), and a warm amber **accent** — all in OKLCH. **Swap one hue number to make the ramp yours.**

```css
@import "tailwindcss";

@theme {
  /* ---------- NEUTRALS (warm-tinted, never pure #000/#fff) ---------- */
  --color-ink-50:  oklch(0.98 0.004 80);   /* off-white background */
  --color-ink-100: oklch(0.96 0.005 80);
  --color-ink-200: oklch(0.92 0.006 80);
  --color-ink-300: oklch(0.86 0.007 75);
  --color-ink-400: oklch(0.72 0.008 70);
  --color-ink-500: oklch(0.58 0.009 65);
  --color-ink-600: oklch(0.47 0.010 60);
  --color-ink-700: oklch(0.38 0.011 55);
  --color-ink-800: oklch(0.27 0.012 50);
  --color-ink-900: oklch(0.20 0.012 45);
  --color-ink-950: oklch(0.15 0.012 45);   /* near-black text */

  /* ---------- PRIMARY (deep teal — distinctive, not indigo) ---------- */
  --color-primary-50:  oklch(0.97 0.02 195);
  --color-primary-100: oklch(0.93 0.04 195);
  --color-primary-200: oklch(0.87 0.07 193);
  --color-primary-300: oklch(0.79 0.10 191);
  --color-primary-400: oklch(0.70 0.12 189);
  --color-primary-500: oklch(0.62 0.13 187);  /* button bg */
  --color-primary-600: oklch(0.53 0.12 186);
  --color-primary-700: oklch(0.44 0.10 185);
  --color-primary-800: oklch(0.35 0.08 185);
  --color-primary-900: oklch(0.28 0.06 185);
  --color-primary-950: oklch(0.20 0.04 185);

  /* ---------- ACCENT (warm amber — sparing, for highlights) ---------- */
  --color-accent-400: oklch(0.82 0.14 70);
  --color-accent-500: oklch(0.76 0.16 65);
  --color-accent-600: oklch(0.68 0.16 60);

  /* ---------- SEMANTIC ---------- */
  --color-success-500: oklch(0.65 0.15 150);
  --color-warning-500: oklch(0.80 0.13 85);
  --color-danger-500:  oklch(0.60 0.20 27);
  --color-info-500:    oklch(0.64 0.14 240);

  /* ---------- TYPOGRAPHY ---------- */
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Fraunces", Georgia, serif;
  --font-mono: "Geist Mono", ui-monospace, monospace;

  --text-xs: 0.75rem;    --text-xs--line-height: 1rem;
  --text-sm: 0.875rem;   --text-sm--line-height: 1.25rem;
  --text-base: 1rem;     --text-base--line-height: 1.6rem;
  --text-lg: 1.25rem;    --text-lg--line-height: 1.75rem;
  --text-xl: 1.5625rem;  --text-xl--line-height: 2rem;
  --text-2xl: 1.953rem;  --text-2xl--line-height: 2.25rem;
  --text-3xl: 2.441rem;  --text-3xl--line-height: 2.5rem;
  --text-4xl: 3.052rem;  --text-4xl--line-height: 1.1;

  /* ---------- SPACING (4px base, 8pt rhythm) ---------- */
  --spacing: 0.25rem;    /* 1 = 4px, 2 = 8px, ... */

  /* ---------- RADII ---------- */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.5rem;

  /* ---------- SHADOWS (tinted toward neutral, layered) ---------- */
  --shadow-sm: 0 1px 2px oklch(0.20 0.012 45 / 0.06);
  --shadow-md: 0 2px 4px oklch(0.20 0.012 45 / 0.06), 0 4px 8px oklch(0.20 0.012 45 / 0.06);
  --shadow-lg: 0 4px 8px oklch(0.20 0.012 45 / 0.06), 0 12px 24px oklch(0.20 0.012 45 / 0.08);

  /* ---------- MOTION ---------- */
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
}

/* Dark mode: remap semantic surfaces via lightness (not shadows) */
@layer base {
  .dark {
    --color-bg:             oklch(0.17 0.012 250); /* near-black, cool navy tint */
    --color-surface:        oklch(0.21 0.012 250); /* card */
    --color-surface-raised: oklch(0.25 0.012 250); /* modal/popover */
    --color-text:           oklch(0.93 0.005 250);
    --color-text-muted:     oklch(0.72 0.008 250);
    --color-border:         oklch(0.30 0.012 250);
  }
}
```

Swap the primary hue (187 = teal) to anything — e.g. 25 for terracotta, 300 for magenta, 145 for emerald, 256 for blue — and because it's OKLCH the whole ramp stays balanced.

---

## The CSS-first `@theme` model

Tailwind v4 abandons `tailwind.config.js` in favor of a CSS-first `@theme` block. The mental model that matters:

- **Tokens become CSS variables AND generate utilities.** A `--color-primary-500` token is available at runtime as a regular CSS custom property *and* generates `bg-primary-500`, `text-primary-500`, `border-primary-500`, etc. One definition, both surfaces.
- **`--spacing` is the base unit** for the whole spacing scale. With `--spacing: 0.25rem`, utility `p-4` = 16px, `gap-2` = 8px, and so on — the 8pt rhythm falls out of a 4px base automatically.
- **Type tokens carry their line-height** via the `--text-*--line-height` companion variable, so `text-lg` ships the right leading with the size.
- Defining colors in OKLCH here is what gives you P3 vividness and matches Tailwind's own palette math.

---

## Surfaces & dark-mode elevation

### Elevation = lightness, not shadows

On dark backgrounds shadows are essentially invisible — so **express elevation with lightness**. Step each surface ~3–5 L points lighter as it floats up:

```
base    L ~10–12%   /* page bg */
sidebar L ~14–16%
card    L ~17–20%
modal   L ~22–26%
popover L ~26–30%
```

Use a near-black base (around L 8–12%) — never pure black, which causes "blooming"/halation around text and leaves no room to express elevation.

### The Material-2 overlay ladder (a relative guide)

If you'd rather not hand-pick every L value, Material 2's dark-theme spec encodes elevation as white-overlay percentages on a `#121212` base — a useful **relative** ladder:

```
1dp = 5%    2dp = 7%    3dp = 8%    4dp = 9%
6dp = 11%   8dp = 12%   12dp = 14%  16dp = 15%   24dp = 16%
```

Apply as `color-mix(in oklch, #fff <pct>%, var(--bg))` or a translucent white overlay. (Material 3 replaced these overlays with a tonal surface-color system — use the percentages as a guide to *relative* lightness steps, not M3 gospel.)

### Other dark-mode adjustments

- **Desaturate and lighten accents on dark.** A vivid blue that's perfect on white turns aggressive on a dark surface; shift it lighter and lower-chroma.
- **Soften text** — avoid pure white on dark; use a high off-white or semi-transparent white. A useful opacity ladder: ~87% high-emphasis, 60% medium, 38% disabled.
- **Borders/separators** sit at L 20–30% on dark.

### Tinted shadows (light mode)

Tint shadows slightly **toward the background hue** rather than pure black — it reads as realistic depth instead of a hard drop. In the example block above, every shadow uses `oklch(0.20 0.012 45 / ...)`, i.e. the neutral's own hue at low alpha, not `#000`. Keep a small, consistent set of elevation levels (sm/md/lg) and layer two soft shadows per step rather than one harsh one.

---

## Radii: concentric nesting

Pick one radius scale and stay consistent (small = neutral/serious, large = friendly/playful, 0 = brutalist/technical). For nested elements, use **concentric radii** so corners stay parallel:

```
inner radius = outer radius − padding
```

A card with `radius-xl` (16px) and 8px of padding around an inner panel should give that panel an 8px radius — otherwise the inner corner looks pinched against the outer one.

---

## Applying this to a real brand

The OKLCH ramp recipe and elevation ladder are the *mechanism* — your brand decisions ride on top of them:

- A **dark-first** product picks a near-black base (e.g. something around `#0a0a0a`) with a restrained accent, then builds surfaces up the lightness ladder above.
- A **light-first** product picks an off-white base (e.g. something around `#fafafa`) with one disciplined accent, and leans on tinted layered shadows for depth.
- A good, safe type pairing to start from: **Space Grotesk** (display) + **Inter** (body) — distinctive headline character against a neutral, screen-optimized body. Swap either to taste.

OKLCH is *how* you build the ramp; temperature, accent hue, and type are *what* make it yours. Pick the hue and the neutral temperature deliberately, validate every text/background and UI pairing for contrast (4.5:1 body, 3:1 large text and UI controls, in both themes), and the rest of the system stays balanced on its own.
