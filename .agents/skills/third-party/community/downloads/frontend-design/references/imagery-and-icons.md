# Imagery & Icons — the values that kill the AI/stock look

Images are **~40–60% of page weight** and **~42% of LCP elements** (Addy Osmani). Get the recipe wrong and you tank both Core Web Vitals and the premium feel. This file is the copy-pasteable how — strategy lives in `/ux-designer`.

## Image optimization recipe

### Format cascade: AVIF → WebP → JPEG/PNG fallback
AVIF compresses ~50%+ better than JPEG; WebP has ~95%+ browser support. Two ways to serve:

**1. `<picture>` with cascading `<source>` (works on any stack, no CDN):**
```html
<picture>
  <source type="image/avif" srcset="/img/hero-640.avif 640w, /img/hero-1280.avif 1280w" sizes="(max-width: 640px) 100vw, 1280px">
  <source type="image/webp" srcset="/img/hero-640.webp 640w, /img/hero-1280.webp 1280w" sizes="(max-width: 640px) 100vw, 1280px">
  <img src="/img/hero-1280.jpg" width="1280" height="720" alt="…"
       fetchpriority="high" decoding="async">
</picture>
```
The browser picks the first `<source>` it understands; `<img>` is the universal floor. **Same aspect ratio across every variant** or `srcset` switches cause layout shift.

**2. Image CDN with `Accept`-header negotiation (preferred when available):**
Cloudflare Images / Imgix / bunny.net / Cloudinary read the request `Accept` header and return AVIF/WebP automatically — you ship one `<img src>` with `srcset` and skip the `<picture>` boilerplate. Most projects already sit behind a CDN like Cloudflare, so if yours does, Image Resizing / on-the-fly transforms are the path of least resistance — no `<picture>` boilerplate to maintain.

### `srcset` + `sizes` — ship resolution-appropriate bytes
Cuts mobile image bytes **60–70%**. `sizes` tells the browser the rendered width *before* layout so it picks the right file:
```html
<img srcset="/card-400.avif 400w, /card-800.avif 800w, /card-1200.avif 1200w"
     sizes="(max-width: 768px) 100vw, 400px"
     src="/card-800.avif" width="800" height="600" alt="…" loading="lazy">
```
Rule of thumb: provide 1×/2× of each layout slot. Keep all `srcset` entries the same aspect ratio.

### ALWAYS reserve space — kills CLS
Set `width`/`height` attributes (intrinsic dimensions, not display size) **or** `aspect-ratio` in CSS. Never ship a responsive image with neither — it's the #1 source of layout shift.
```css
img { height: auto; }                 /* let width attr + this scale fluidly */
.media { aspect-ratio: 16 / 9; }      /* when dimensions are unknown at build */
```

### Loading priority — the hero is sacred
- **Below the fold:** `loading="lazy"`.
- **LCP / hero image:** NEVER lazy-load it. Mark it `fetchpriority="high"`, leave it eager, and `<link rel="preload" as="image">` in `<head>` (with `imagesrcset`/`imagesizes` matching the `<img>`). Lazy-loading the LCP image is the most common self-inflicted LCP regression.
```html
<link rel="preload" as="image" href="/img/hero-1280.avif"
      imagesrcset="/img/hero-640.avif 640w, /img/hero-1280.avif 1280w"
      imagesizes="(max-width: 640px) 100vw, 1280px">
```

### Use the right tool for the job
- **SVG** for logos, icons, UI marks, simple illustration — infinitely crisp, tiny, themeable via `currentColor`.
- **CSS gradients** instead of background-image JPEGs wherever possible (zero bytes, no request, scales free).
- Raster (AVIF/WebP) only for actual photography/screenshots.

### Framework helpers vs. doing it by hand
Next.js gets this for free via `next/image` (auto format/resize/lazy/dimensions); Astro (`<Image />`) and Nuxt have equivalents. On stacks without a built-in image component — e.g. Laravel/Blade — pick one of these:
- **Image CDN (least effort):** front images with Cloudflare Image Resizing / Imgix / bunny.net / Cloudinary; emit plain `<img srcset>` and let the CDN negotiate format by `Accept` header.
- **Glide** (`league/glide` + a Laravel adapter such as `spatie/laravel-glide`): on-the-fly resize/convert via URL params (`?w=800&fm=webp`); cache derivatives to disk/S3.
- **Intervention Image** at upload/build time: pre-generate AVIF + WebP + fallback into a `<picture>` partial.

A reusable Blade component keeps it DRY:
```blade
{{-- <x-picture src="hero" w="640,1280" ratio="16/9" :priority="true" alt="…" /> --}}
@props(['src','w','ratio'=>null,'priority'=>false,'alt'=>''])
<picture>
  <source type="image/avif" srcset="@foreach(explode(',',$w) as $width){{ asset("img/{$src}-{$width}.avif") }} {{ $width }}w@if(!$loop->last), @endif @endforeach">
  <source type="image/webp" srcset="@foreach(explode(',',$w) as $width){{ asset("img/{$src}-{$width}.webp") }} {{ $width }}w@if(!$loop->last), @endif @endforeach">
  <img src="{{ asset("img/{$src}-".explode(',',$w)[array_key_last(explode(',',$w))].'.jpg') }}"
       alt="{{ $alt }}" decoding="async"
       loading="{{ $priority ? 'eager' : 'lazy' }}"
       fetchpriority="{{ $priority ? 'high' : 'auto' }}"
       @if($ratio) style="aspect-ratio: {{ $ratio }}" @endif>
</picture>
```

## Iconography

**Pick ONE family and never mix.** Consistent stroke width, grid, and optical size is what separates polished from cobbled-together. Quick rundown (all MIT/OFL, tree-shakable, with framework packages):

| Family | Character | Best for |
|---|---|---|
| **Lucide** | Clean stroke (Feather fork) | Modern default — but *so* ubiquitous (baked into AI output/templates) it can read generic |
| **Phosphor** | 6 weights (thin→fill) + duotone | Stylistic range in one family; good when you want a personality dial |
| **Tabler** | 5,900+ icons, 24px grid, 2px stroke | Dashboards / data-heavy admin UIs |
| **Heroicons** | Tailwind team, small/familiar set | Fast + safe, less distinctive |
| **Iconoir / Hugeicons** | More characterful line work | When you specifically want to escape the Lucide/Heroicons sameness |

Rule of thumb: Lucide is a fine default on most products, but for a flagship marketing surface reach for Phosphor or Iconoir to dodge the generic read.

**Wiring (every family, same rules):**
```html
<!-- Decorative: hide from AT, inherit color -->
<svg aria-hidden="true" focusable="false" width="20" height="20"
     fill="none" stroke="currentColor" stroke-width="2">…</svg>

<!-- Icon is the ONLY content: it must be labeled -->
<button aria-label="Close" type="button">
  <svg aria-hidden="true" …>…</svg>
</button>
```
- Always `fill="currentColor"` / `stroke="currentColor"` so icons inherit theme + dark-mode color from the parent — never hardcode hex on an icon.
- `aria-hidden="true"` on decorative icons; an adjacent text label or `aria-label` whenever the icon stands alone.
- Match icon optical size to the font: 16–20px next to body text, 24px for nav/touch targets. Don't scale a 24px-grid icon down to 14px — it goes muddy; grab the family's small build.

## Art direction — beating the stock/AI look

The execution levers (the *why* is in `/ux-designer`):

- **One unifying treatment across every image** so a stock library or mixed sources read as a coherent set. Pick one and apply globally:
  - **Duotone** map shadows→brand-dark, highlights→brand-light.
  - **Brand-color overlay / gradient map** at ~10–25% over photos.
  - **Subtle grain/texture** to break the "too-perfect" AI smoothness.
```css
/* Brand-color overlay — drop on any <figure> wrapping a photo.
   Swap the two oklch() stops for your own ramp; these are placeholders. */
.media-branded { position: relative; }
.media-branded::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(135deg,
    oklch(0.62 0.19 256 / 0.18),   /* your brand accent A */
    oklch(0.58 0.22 295 / 0.18));  /* your brand accent B */
  mix-blend-mode: overlay; pointer-events: none;
}
/* Duotone via SVG filter or CSS — quick CSS approximation: */
.media-duotone { filter: grayscale(1) contrast(1.05); background: var(--brand-500); }
.media-duotone img { mix-blend-mode: luminosity; opacity: 0.9; }
```
- **Consistent color grade + lighting/angle** across a photo set — same warmth, same contrast curve. A mismatched grade is the #1 tell of a stitched-together stock gallery.
- **Brand-specific gradients, interpolated in OKLCH** — NOT the default purple→blue "Tech Bro Gradient." Multi-stop or mesh, derived from your palette. OKLCH interpolation avoids the muddy gray midpoint that sRGB/HSL gradients fall into:
```css
/* The PORTABLE rule: interpolate in OKLCH and derive stops from YOUR ramp,
   not the default lavender→blue. The values below are placeholders. */
.hero-mesh {
  background:
    radial-gradient(at 20% 20%, oklch(0.62 0.19 256) 0px, transparent 50%),
    radial-gradient(at 80% 30%, oklch(0.58 0.22 295) 0px, transparent 50%),
    radial-gradient(at 50% 90%, oklch(0.55 0.15 220) 0px, transparent 55%),
    var(--color-bg);
}
.brand-fade { background: linear-gradient(in oklch 135deg, var(--brand-500), var(--brand-700)); }
```
  **Applying it to a real brand:** a dark-first product (e.g. a near-black `#0a0a0a` surface with a restrained two-color accent) and a light-first product (e.g. an off-white `#fafafa` surface with one accent) each derive their stops from their *own* ramp — same OKLCH technique, different hues. Never paste another brand's stops in.
- **Real product UI screenshots over abstract illustration** for SaaS — the near-universal 2026 pattern is *show the product working*. Reserve custom illustration for when a consistent house style genuinely reinforces brand (Notion's characters); otherwise it signals "template."

## Anti-patterns

- Lazy-loading the hero/LCP image (or forgetting `fetchpriority="high"` on it).
- Responsive image with no `width`/`height`/`aspect-ratio` — guaranteed CLS.
- `srcset` variants at different aspect ratios — causes shift when the browser swaps source.
- Mixing two icon libraries on one surface (mismatched stroke weights scream amateur).
- Hardcoding hex on icons instead of `currentColor` — breaks dark mode.
- The default purple→blue gradient and "suspiciously smooth" AI illustration — the exact tells 2025/2026 design is reacting against.
- Background-image JPEGs where a CSS gradient or SVG would do (free bytes spent for nothing).
