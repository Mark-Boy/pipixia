# Visual Design

Visual design encompasses color theory, typography, layout, and the principles that make interfaces aesthetically pleasing and functional.

This file is the **strategy / decision-framework** layer — *what* to choose and *why*. For copy-pasteable OKLCH ramps, the elevation ladder, and the Tailwind v4 `@theme` block, point to `frontend-design/references/design-tokens.md`; for the image-optimization recipe (AVIF/WebP, `srcset`, LCP) point to `frontend-design/references/imagery-and-icons.md`. Don't duplicate values here — decide here, fetch values there.

The throughline across all of it: **distinctiveness comes from restraint plus one or two strong, intentional choices** — a real type system, a near-neutral palette with one disciplined accent, generous whitespace, purposeful motion. Not neon-on-black gradients and cliché hero layouts. That combination is the generic "AI vibe-coded" tell; the whole 2025/2026 design conversation is a backlash against it.

---

## Color Theory

### Color Psychology

Colors evoke specific emotions and influence user behavior.

| Color | Associations | Common Uses |
|-------|--------------|-------------|
| **Red** | Energy, urgency, passion, danger | Errors, sales, CTAs |
| **Orange** | Enthusiasm, creativity, warmth | Notifications, CTAs |
| **Yellow** | Optimism, warning, attention | Warnings, highlights |
| **Green** | Growth, success, nature, calm | Success states, eco themes |
| **Blue** | Trust, stability, professionalism | Corporate, tech, links |
| **Purple** | Luxury, creativity, mystery | Premium products |
| **Pink** | Playful, romantic, youthful | Fashion, lifestyle |
| **Black** | Sophistication, power, elegance | Luxury, fashion |
| **White** | Purity, simplicity, cleanliness | Minimalist designs |
| **Gray** | Neutral, professional, balanced | Backgrounds, borders |

### The 60-30-10 Rule

A balanced color palette distribution:

```
60% - Dominant color (backgrounds, large areas)
30% - Secondary color (supporting elements)
10% - Accent color (CTAs, highlights)
```

**Example:**
```css
:root {
  --color-dominant: #ffffff;    /* 60% - Background */
  --color-secondary: #f5f5f5;   /* 30% - Cards, sections */
  --color-accent: #0066cc;      /* 10% - Buttons, links */
}
```

**The non-obvious part: the brand color is NOT the most-used color.** In real UIs the 60% is a neutral (background/surface), the 30% is a secondary neutral, and the brand/primary lives only in the 10% — CTAs, links, emphasis. Think Netflix or Target: mostly neutral, with a signature red splash. New designers do the opposite and flood the screen with brand color; that's what reads as amateur and exhausting. Color earns its first-impression weight precisely because it's rationed: per the Institute for Color Research (CCICOLOR), people form a subconscious judgment about a product within ~90 seconds of first viewing, and **between 62% and 90% of that assessment is based on color alone**.

### Great UIs are mostly neutrals

You cannot build a real interface from "five perfect swatches." Per *Refactoring UI* and EightShapes (Nathan Curtis), what you actually need:

- **Neutrals (grays): 8–10 shades.** This is the scaffolding of *everything* — text, backgrounds, panels, borders, form controls. Build by picking the darkest (body text) and lightest (subtle off-white background) first, then a 700 and a 300, then fill the gaps. Trust your eyes, not the numbers.
- **Primary brand color: 1, maybe 2**, each with ~9–10 shades. Pick the base (≈500) as "a shade that would work well as a button background."
- **Semantic colors** — success / warning / danger / info — each usually needs a light tint (bg), a mid (icon/border), and a dark (text) variant.

Hard-won rules worth internalizing:

- **Never pure #000 or pure #fff for large areas.** Pure black on white is 21:1 — harsh, causes haloing/eye strain, reads cheap. Use a near-black (a very dark desaturated value) and an off-white instead.
- **Tint your grays toward the brand hue.** Pure grayscale doesn't exist in nature and can feel unnatural. Shift gray hue slightly toward your brand color (warm grays lean red/yellow, cool grays lean blue) for a cohesive, premium feel.
- **Avoid muddy medium grays.** Nothing reads accessibly on a medium gray, and a UI built on them looks "wireframey" and unfinished. Provide a few light grays and a few dark grays; skip the swampy middle.
- **Temperature is a brand decision.** Warm neutrals (slightly yellow/red) feel human, editorial, inviting. Cool neutrals (slightly blue) feel technical, clean, corporate. Pick deliberately — it sets the whole mood before any content loads.

For the actual ramp recipe (lock a lightness array, solve for chroma, swap one hue number to make it yours) see `frontend-design/references/design-tokens.md`.

### Build color in OKLCH, not HSL/HEX

This is the single biggest practical upgrade to a color workflow, and a *principle* worth defaulting to on any new project. `oklch(L C H)` — lightness, chroma, hue — is **perceptually uniform**: one lightness value looks equally bright across every hue. HSL is not — `hsl(220 100% 50%)` (blue) and `hsl(60 100% 50%)` (yellow) share a "lightness" number but look wildly different in brightness, which is why naive `lighten()`/`darken()` math drifts your blue toward purple and turns gradients muddy in the middle. OKLCH keeps a hue on-hue from 50→950, interpolates cleanly, and reaches P3 wide-gamut vividness. Tailwind v4 ships its whole palette in OKLCH for exactly these reasons. Decide to use it here; get the ramp values from the tokens ref.

### Color Harmonies — and when to reach for each

| Harmony | Description | When to use |
|---------|-------------|-------------|
| **Monochromatic** | One hue across many lightness/chroma steps | The most foolproof route to a sophisticated, cohesive look — when in doubt, start here |
| **Complementary** | Opposite hues; maximum contrast | A punchy single accent against a dominant hue; energetic but use sparingly |
| **Analogous** | 2–3 adjacent hues | Calm, cohesive, naturally harmonious; good for soft/editorial moods |
| **Triadic** | Three hues evenly spaced (120°) | Vibrant but balanced — use one dominant + two accents, never three equals |
| **Split-complementary** | Base + the two neighbors of its complement | The high-contrast energy of complementary with less tension; a safer "vibrant" |

The harmony is a *starting relationship*, not the finished palette — you'll still expand each chosen hue into a full 8–10-step ramp and let neutrals carry 60% of the surface.

### Contrast for Accessibility

```css
/* WCAG 2.2 Requirements */

/* Normal text (< 18pt) */
/* Minimum contrast: 4.5:1 (AA), 7:1 (AAA) */

/* Large text (≥ 18pt or 14pt bold) */
/* Minimum contrast: 3:1 (AA), 4.5:1 (AAA) */

/* UI Components & graphical objects (1.4.11 Non-text Contrast) */
/* Minimum contrast: 3:1 against adjacent colors */
/* Applies to input borders, button boundaries, meaningful icons, */
/* focus indicators, and chart parts. */
```

**WCAG is the floor, not the ceiling.** A 4.52:1 pass is still hard for some users — aim higher for body text where you can — but don't swing to pure-black-on-white (21:1), which can trigger discomfort or migraines. Contrast is the single most common accessibility failure on the web: the **WebAIM Million 2026 report** (analysis of the top 1,000,000 home pages) found low-contrast text on **83.9% of home pages** (up from 79.1% in 2025), the most commonly-detected issue, averaging 34 instances per page. It's increasingly a legal requirement too: the **EU European Accessibility Act (Directive 2019/882) entered into force 28 June 2025**, with national penalties reaching up to €100,000 per violation or 4% of annual revenue (e.g. Germany's BFSG); the ADA governs in the US. Treat AA contrast as a non-negotiable CI check (axe-core / Pa11y / Lighthouse).

> Emerging: **APCA** (Advanced Perceptual Contrast Algorithm), being developed for WCAG 3, models perception better than the 2.x ratio. Worth tracking, but build to WCAG 2.2 AA today — that's the legal/standard floor.

### Colorblind-Safe Design

Color vision deficiency affects **1 in 12 men (~8%) and 1 in 200 women (~0.5%)** — roughly 300 million people worldwide (Colour Blind Awareness). Never rely on color alone (WCAG 1.4.1): pair it with an icon, label, or pattern, especially for status.

```
Best Practices:
- Don't use color alone to convey meaning
- Add icons, patterns, or text labels
- Test with colorblind simulation tools
- Use sufficient contrast between colors
- Avoid red/green combinations for critical info
```

### Dark Mode Considerations

```css
/* Use CSS custom properties for theming */
:root {
  --bg-primary: #ffffff;
  --text-primary: #1a1a1a;
  --accent: #0066cc;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a1a1a;
    --text-primary: #f5f5f5;
    --accent: #66b3ff;
  }
}

/* Reduce contrast slightly in dark mode */
/* Pure white (#fff) on black (#000) can cause eye strain */
```

**Dark mode done well — the decisions:**

- **Never pure black.** Use a dark gray / near-black base around L 8–12% (e.g. `#121212` Material, `#0d1117`/`#0f172a` deep-navy SaaS feel, or a warm charcoal). Pure black causes blooming/halation around text and leaves no room to express elevation.
- **Express elevation with lightness, not shadows** — shadows are invisible on dark surfaces. Each step is ~3–5 lightness points lighter: base → sidebar → card → modal/drawer → popover. (Material 2 encoded this as white-overlay percentages on `#121212`; Material 3 replaced them with a tonal surface system. Use the percentages as a guide to *relative* steps, not gospel.)
- **Desaturate and lighten accents.** A vivid blue that's perfect on white turns aggressive on dark; shift toward lighter, less-saturated tones.
- **Soften text.** Avoid pure white on dark; use ~`#E2E8F0`/`#F1F5F9` or semi-transparent whites. Material's opacity tiers: ~87% high-emphasis, 60% medium, 38% disabled.
- **Use semantic tokens** so light and dark are two mappings of the same intent, and respect `prefers-color-scheme`.

The full surface/elevation ladder lives in `frontend-design/references/design-tokens.md`.

### Applying this to a real brand

Translate brand adjectives into the palette before touching a swatch. Two worked directions, to show the range:

- **A dark-first surface** — e.g. a near-black like `#0a0a0a` (not `#000`) with a restrained cool accent — reads confident, technical, "product-led." Best for developer tools, AI products, anything that wants to feel sharp and modern.
- **A light-first surface** — e.g. an off-white like `#fafafa` (not `#fff`) with a single accent — reads clean, calm, approachable. Best for content, dashboards, and anything where long reading sessions matter.

Pick the temperature and the one accent hue deliberately from the brand's point of view; everything else stays neutral. Public reference points for "one disciplined accent": Stripe's blurple **#635BFF**, Linear's desaturated indigo **#5E6AD2**, Raycast's red **#FF6363** — each used with heavy restraint against a near-neutral foundation. Note this dark-surface-plus-one-neon-accent formula is itself becoming a cliché ("the new 'blue for trust'"); take the *principles* (contrast, whitespace, restraint, real product imagery) and bring your own palette and temperature rather than copying the dark-purple-gradient template.

---

## Typography

### Font Selection

**Categories:**
- **Sans-serif:** Clean, modern, screen-friendly (Roboto, Inter, SF Pro)
- **Serif:** Traditional, authoritative, editorial (Georgia, Merriweather)
- **Monospace:** Technical, code, data (Fira Code, JetBrains Mono)

**Guidelines:**
- **Two families max** — one for headings, one for body. A third only as a sparing mono accent. Hierarchy comes from size, weight, and color, not from more typefaces.
- **Favor fonts with 5+ weights.** *Refactoring UI*: "ignore typefaces with less than five weights." Weight contrast is most of how you build hierarchy in a one- or two-family system.
- **Prefer the variable build** — all weights/axes in one file means a smaller payload and finer control. Self-host or `preconnect`, subset to needed glyphs, load only the weights you use, always `font-display: swap`.

```css
/* System font stack for performance */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
             Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
```

**Recommended typefaces (high quality, mostly free):**

- **Workhorse sans (UI/body):** **Inter** — designed for screens with a tall x-height; the de facto modern SaaS default (Linear, Notion, Figma, GitHub). Also Geist (Vercel's open-source face), Plus Jakarta Sans, Manrope, Hanken Grotesk, Source Sans 3, IBM Plex Sans, Figtree, Work Sans.
- **Distinctive display/headline:** Fraunces (variable, optical-size axis, old-style charm), Bricolage Grotesque, Space Grotesk, Clash Display, General Sans, Cabinet Grotesk, Syne.
- **Serifs (editorial/premium):** Source Serif 4, Lora, Playfair Display, Libre Baskerville, Cormorant Garamond, Newsreader.
- **Mono (code/technical accent):** Geist Mono, JetBrains Mono, IBM Plex Mono, Space Mono, Fira Code.

**Strong pairings (pick one):**

- **Inter + Inter** (one family, weight contrast) — cleanest, safest; most SaaS products do exactly this.
- **Plus Jakarta Sans (headings) + Inter (body)** — subtle geometric warmth over a neutral body; both variable.
- **Fraunces (headings) + Inter/Lora (body)** — editorial character with a modern body.
- **Space Grotesk + Space Mono** — technical / AI / dev-tool vibe.
- **Playfair Display + Source Sans 3** — classic high-contrast elegance.

Avoid pairing two similar geometric sans (e.g. Poppins + Nunito) — that produces hierarchy *confusion*, not contrast. The brands that win on type (Stripe's Söhne, Vercel's Geist, Mercury's Arcadia) treat custom or carefully-chosen type as a brand moat — but a quality variable workhorse used with strong weight contrast gets you most of the way.

### Size Scale

Pick a base (16px) and a **modular ratio**, then multiply/divide. The ratio is a design decision — it sets how dramatic the jumps between levels feel:

| Ratio | Name | When to use |
|-------|------|-------------|
| **1.125** | Major Second | Subtle, dense — dashboards, content-heavy apps |
| **1.200** | Minor Third | Balanced — very common for product UI |
| **1.250** | Major Third | Clear — marketing-friendly |
| **1.333** | Perfect Fourth | Strong hierarchy — good default for marketing sites |
| **1.5 / 1.618** | Perfect Fifth / Golden | Dramatic, editorial — big headlines |

**Ready-to-use scale (16px base, ~1.25):** `12 / 14 / 16 / 20 / 25 / 31 / 39 / 49 / 61px`.

```css
/* Type scale with 1.25 ratio (Major Third) */
:root {
  --text-xs: 0.75rem;   /* 12px - Captions */
  --text-sm: 0.875rem;  /* 14px - Small text */
  --text-base: 1rem;    /* 16px - Body (minimum) */
  --text-lg: 1.25rem;   /* 20px - Large body */
  --text-xl: 1.5625rem; /* 25px - H3 */
  --text-2xl: 1.953rem; /* 31px - H2 */
  --text-3xl: 2.441rem; /* 39px - H1 */
  --text-4xl: 3.052rem; /* 49px - Display */
}
```

Use `clamp()` for fluid type so an H1 scales between mobile and desktop without extra breakpoints, e.g. `font-size: clamp(2rem, 1.5rem + 2.5vw, 3.5rem);`.

**Minimum sizes:**
- Body text: never below **16px** for primary body on web — use `rem` so user zoom/settings are respected.
- Mobile body: 16px (also prevents zoom-on-focus on iOS).
- Small text: 12px (use sparingly).

### Line Height

```css
/* Optimal line heights */
body {
  line-height: 1.5; /* 1.5-1.6 for body text */
}

h1, h2, h3 {
  line-height: 1.2; /* 1.1-1.3 — large type needs less leading */
}

.compact {
  line-height: 1.3; /* UI elements, buttons */
}
```

Body wants **1.5–1.6**; headings want **1.1–1.3** (larger type needs proportionally less leading, or it floats apart). Set line heights to multiples of 4px (20/24/28/32) so text sits on a 4px sub-grid and vertical rhythm stays consistent.

### Line Length

Optimal reading **measure: 45–75 characters per line** (~66 is the classic sweet spot — Bringhurst). WCAG 1.4.8 caps it at 80.

```css
/* Constrain line length — prefer ch so it tracks font size */
.prose {
  max-width: 66ch; /* ~66 characters */
}

/* Alternatively */
.content {
  max-width: 700px;
  padding: 0 1rem;
}
```

### Text Alignment

```
Left-aligned (default):
- Best for readability
- Consistent starting point
- Recommended for body text

Center-aligned:
- Short text only (headlines, CTAs)
- Creates visual anchor

Right-aligned:
- Numbers in tables
- RTL languages
- Avoid for body text

Justified:
- Creates uneven word spacing
- Avoid for web (no hyphenation)
- WCAG discourages for accessibility
```

### Fluid Typography

```css
/* Responsive font sizes with clamp() */
h1 {
  font-size: clamp(2rem, 5vw + 1rem, 4rem);
}

body {
  font-size: clamp(1rem, 2.5vw, 1.25rem);
}
```

### Amateur typography mistakes (the tells)

A quick self-check — every one of these reads as "unfinished":

- Too many sizes (use a scale, not ad-hoc px values).
- Insufficient size *contrast* between levels (jumps too small to establish hierarchy).
- Centered long-form body text (only headlines/CTAs should center).
- Justified text without hyphenation (rivers of uneven word spacing; WCAG discourages it).
- Placeholder gray used as real text (fails contrast and disappears on focus).
- Body text under 16px.
- Line length too long (past ~75ch).
- Headings with too-loose leading (large type needs *tighter* line-height, not the body value).

---

## Visual Hierarchy

### Establishing Hierarchy

1. **Size** - Larger = more important
2. **Weight** - Bolder = more important
3. **Color** - Contrast draws attention
4. **Position** - Top/left (LTR) = primary
5. **Space** - Isolation = emphasis
6. **Depth** - Shadows, layers

### Heading Hierarchy

```html
<!-- Single H1 per page -->
<h1>Page Title</h1>
  <h2>Section</h2>
    <h3>Subsection</h3>
      <h4>Detail</h4>
  <h2>Another Section</h2>
```

### Visual Weight

```css
/* Primary action - highest weight */
.btn-primary {
  background: var(--accent);
  color: white;
  font-weight: 600;
}

/* Secondary action - medium weight */
.btn-secondary {
  background: transparent;
  border: 2px solid var(--accent);
  color: var(--accent);
}

/* Tertiary action - lowest weight */
.btn-tertiary {
  background: transparent;
  color: var(--accent);
  text-decoration: underline;
}
```

---

## Whitespace and Spacing

### The Role of Whitespace

- **Breathing room** - Reduces visual clutter
- **Grouping** - Related items closer together
- **Focus** - Isolation creates emphasis
- **Readability** - Improves comprehension

**Whitespace is the cheapest luxury.** The rule of thumb from the design-led leaders (Stripe / Linear / Vercel): *take the spacing that feels like enough, then double it.* Inconsistent vertical rhythm is the #1 tell of an unfinished UI; over-generous, consistent rhythm is the cheapest way to read as premium.

### 8-point grid (size and space in multiples of 8)

Size and space everything in multiples of **8** (8/16/24/32/40/48/64/80/96…), with **4px** as a permitted half-step for tight gaps (icon-to-label). Why 8: it divides cleanly, scales across device pixel ratios, and Apple/Google both recommend it. Pair an **8pt UI grid** (layout/components) with a **4pt baseline grid** (text rhythm — set line heights to multiples of 4).

### Spacing Scale

```css
/* Consistent spacing scale (4px base, 8pt rhythm) */
:root {
  --space-xs: 0.25rem;  /* 4px */
  --space-sm: 0.5rem;   /* 8px */
  --space-md: 1rem;     /* 16px */
  --space-lg: 1.5rem;   /* 24px */
  --space-xl: 2rem;     /* 32px */
  --space-2xl: 3rem;    /* 48px */
  --space-3xl: 4rem;    /* 64px */
}
```

**The "internal ≤ external" rule:** padding *inside* an element should be ≤ the space *separating* it from its neighbors, so groups read as groups (Gestalt proximity). If a card's inner padding exceeds the gap between cards, the grouping breaks and everything floats.

### Applying Spacing

```css
/* Consistent component spacing */
.card {
  padding: var(--space-lg);
  margin-bottom: var(--space-xl);
}

/* Related items closer */
.form-field label {
  margin-bottom: var(--space-xs);
}

/* Distinct sections further */
.section + .section {
  margin-top: var(--space-3xl);
}
```

---

## Layout Principles

### Grid Systems

Use the right tool for each dimension: **Flexbox** for one-dimensional rows/columns and component internals; **Grid** for two-dimensional page/section layout; **subgrid** to align nested items to a parent grid. A **12-column grid** with 24px (1.5rem) gutters is a clean, on-grid desktop default; container margins ~16px on mobile, ~60px+ on a 1440px frame.

```css
/* CSS Grid for page layout */
.page {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--space-lg);
}

/* Flexbox for component layout */
.card-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
}
```

### Reading patterns: F vs Z

Guide the eye with size, weight, color, and spacing along the path users actually scan:

- **F-pattern** — for text-heavy, scannable pages (articles, search results, dashboards). Users read across the top, then scan down the left edge. Put the most important words at the start of headings and the top-left.
- **Z-pattern** — for simpler landing pages with a clear single path: logo (top-left) → nav/CTA (top-right) → diagonal sweep → hero → primary CTA (bottom-right). Use it when there's one action you want and little to read.

### Responsive: container queries over media queries (for components)

```css
/* Mobile-first breakpoints (for page/section layout) */
@media (min-width: 640px)  { /* tablet portrait */ }
@media (min-width: 768px)  { /* tablet landscape */ }
@media (min-width: 1024px) { /* desktop */ }
@media (min-width: 1280px) { /* large desktop */ }
```

Media queries answer to the *viewport* — fine for page-level layout. But a reusable component (card, sidebar, widget) lives in different contexts at different widths, so it should respond to **its own container's width**, not the viewport. **Container queries** (first-class in Tailwind v4) are the right tool for component-level responsiveness — the same card adapts correctly whether it's in a wide main column or a narrow sidebar, with no viewport-coupled assumptions.

```css
.card-wrapper { container-type: inline-size; }

@container (min-width: 400px) {
  .card { grid-template-columns: auto 1fr; } /* side-by-side once the container is wide enough */
}
```

And reach for **`clamp()`** on type and spacing to cut breakpoint count entirely — one fluid rule often replaces three discrete media-query steps.

### Content Alignment

```css
/* Center content with max-width */
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-md);
}
```

---

## Imagery & Art Direction

Imagery is where the "AI/stock look" most often gives a product away — and where deliberate art direction most cheaply buys credibility.

### Beat the generic stock/AI look

- **Avoid the generic stock photo and the "suspiciously smooth" AI-illustration style.** Prefer original or commissioned photography. When you must use stock, **heavily art-direct it**: a consistent color grade, consistent lighting/angle, and a unifying treatment (duotone, a subtle brand-color overlay or gradient map, grain/texture) across every image so the set reads as one intentional library rather than a grab-bag. 2025/2026 explicitly rewards human-made, textured, original imagery over the too-perfect aesthetic.
- **Real product UI beats abstract illustration** for SaaS — it's the near-universal 2026 pattern. Show the product *working*: a real screenshot (cropped and composed, integrated with type) outperforms a decorative blob or generative illustration almost every time. Treat photography and illustration as *content*, not background filler.
- **Tasteful gradients only:** brand-specific, multi-stop or mesh gradients used as accents — not the default purple→blue "Tech Bro Gradient." Interpolate in OKLCH for clean transitions instead of a muddy gray middle.
- **Custom illustration** is worth it only when a consistent style genuinely reinforces brand personality. Otherwise restraint plus real product imagery is the safer bet; the default generative-illustration style just signals "template."

### Iconography

- **Pick one icon family and stick to it** — consistent stroke width, grid, and optical sizing. Mixing libraries is an immediate tell. Strong MIT/OFL options: **Lucide** (the clean modern default — but so common it can read as generic), **Phosphor** (six weights incl. duotone), **Tabler** (5,900+ on a 24px grid, great for dashboards), **Heroicons** (small, familiar), **Iconoir / Hugeicons** (more distinctive if you want to escape the Lucide sameness).
- Use `currentColor` so icons inherit theme/dark-mode color; `aria-hidden` on decorative icons; a text label or `aria-label` whenever an icon is the only content.

### The how-to lives in the imagery ref

For the executable recipe — AVIF→WebP→JPEG/PNG cascade, `srcset` + `sizes`, `width`/`height` to prevent CLS, lazy-below-fold vs eager `fetchpriority="high"` on the LCP/hero image — see `frontend-design/references/imagery-and-icons.md`. Performance *is* aesthetic: images are ~40–60% of page weight and ~42% of LCP elements, so getting this wrong tanks both Core Web Vitals and the premium feel.

---

## 2025 Trends

### AI-Adaptive Interfaces
- Colors and layouts that adjust based on user behavior
- Personalized visual preferences
- Context-aware theming

### Warm, Soft Colors
- Moving away from stark whites
- Beige, pale pink, peach tones
- Psychologically inviting

### Fluid Design
- Dynamic, responsive everything
- Container queries
- Fluid spacing and typography

### Glassmorphism (Continued)
- Frosted glass effects
- Subtle transparency
- Depth through blur

---

## Tools and Resources

### Color
- [Coolors](https://coolors.co/) - Palette generator
- [Adobe Color](https://color.adobe.com/) - Color wheel
- [Contrast Checker](https://webaim.org/resources/contrastchecker/)

### Typography
- [Type Scale](https://type-scale.com/) - Visual calculator
- [Fontpair](https://fontpair.co/) - Font combinations
- [Google Fonts](https://fonts.google.com/)

### Design Systems
- [Tailwind UI](https://tailwindui.com/)
- [Material Design](https://m3.material.io/)
- [Apple HIG](https://developer.apple.com/design/)

---

## Related references (for values & execution)

- **`frontend-design/references/design-tokens.md`** — the OKLCH ramp recipe, neutral scale, surface/elevation ladder, and a ready Tailwind v4 `@theme` block. Decide *what* here; copy the *values* there.
- **`frontend-design/references/imagery-and-icons.md`** — the image-optimization recipe (AVIF/WebP/`srcset`/LCP) and icon wiring.
- **`23-modern-ui-patterns-2026.md`** (this folder) — the 2026 "is this shippable?" filter and per-surface patterns.

---

## Sources

- [Refactoring UI](https://www.refactoringui.com/) — Adam Wathan & Steve Schoger (palette/type/spacing method)
- EightShapes — Nathan Curtis (design-tokens, neutral-scale guidance)
- [WebAIM Million 2026](https://webaim.org/projects/million/) — contrast-failure prevalence
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) / W3C Design Tokens Community Group
- Institute for Color Research (CCICOLOR) — 90-second / 62–90% color stat
- [Practical Typography](https://practicaltypography.com/), Bringhurst *The Elements of Typographic Style*
- Material Design 2/3; Apple Human Interface Guidelines; Nielsen Norman Group; rsms.me (Inter)
