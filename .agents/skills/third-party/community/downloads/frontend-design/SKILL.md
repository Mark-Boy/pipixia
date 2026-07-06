---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics.
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

## Stack Awareness

Detect the project's stack and match the implementation approach. Read existing config files (`package.json`, `tailwind.config.*`, `globals.css`, Blade layouts) before writing anything.

### Next.js / App Router projects
- Server Components by default; `'use client'` only for state/interactivity
- If the project ships a custom CSS design system, USE IT — do not introduce Tailwind
- If the project ships Tailwind, USE IT — do not introduce a parallel custom system
- Prefer CSS-only animation with Intersection Observer over animation libraries
- Reuse existing design tokens (`--color-*`, `--space-*`, `--font-*`, `--ease-*`) instead of inventing new ones

### Laravel projects (Blade + Alpine / Livewire)
- Blade templates with component syntax (`<x-button>`, `<x-layout>`) and slots
- Tailwind CSS is the standard — don't bolt on custom CSS unless the project already does
- Alpine.js for client state; Livewire if present
- If the project uses Tailwind JIT, remember: new utility classes must appear in scanned files for the bundle to include them. Run the build after adding novel classes.

### Standalone pages (landing pages, tools, microsites)
- Plain HTML/CSS/JS, self-contained, no build step
- Maximum creative freedom — these are where bold aesthetic experiments shine

## Design Thinking

Before coding, understand the context and commit to a clear aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Match the project's existing aesthetic, or if greenfield, pick a direction: brutally minimal, luxury/refined, editorial/magazine, retro-futuristic, brutalist/raw, art deco/geometric, industrial/utilitarian, etc.
- **Constraints**: Which stack? Server or client component? Existing design tokens?
- **Differentiation**: What makes this memorable? What's the one detail someone will notice?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work — the key is intentionality, not intensity.

Then implement working code that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that serve the context. If the project has an established pairing, use it. Otherwise pick distinctive, characterful fonts — avoid generic defaults (Arial, Roboto, system fonts when not intentional). Pair a display font with a refined body font.
- **Color & Theme**: Commit to a cohesive palette. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: CSS-only animations preferred. Focus on high-impact moments — one well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise. A solid default: `cubic-bezier(0.16, 1, 0.3, 1)` easing, 400ms duration.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth. Apply gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, and grain overlays where they serve the design.

## 2026 Aesthetic Baseline (what separates premium from generic AI-slop)

The dominant 2026 web aesthetic is **disciplined restraint** — not flashy trends. Use these as filters before shipping:

**Foundations (set these first):**
- **Build color in OKLCH, not HEX/HSL.** OKLCH is perceptually uniform — equal lightness values look equally bright across hues, gradients don't go muddy, and dark/light shades stay on-hue. It's the single biggest practical upgrade to a color workflow (see `references/design-tokens.md`).
- **Near-neutral foundation + one disciplined accent.** The Linear/Stripe/Vercel model: neutrals dominate the screen, the brand color is the 10% splash on CTAs and emphasis — not the most-used color.
- **The #1 AI tell is the "Tech Bro Gradient"** — a purple→blue mesh on a near-black background (the OpenAI/Anthropic/Midjourney-derived look, now everywhere on ProductHunt). Avoid it. Reach for a brand-specific gradient system and an off-black with a subtle hue (warm charcoal, deep navy) rather than `#000`.

**In:**
- Typography as structure, not decoration — coherent hierarchy on a defined scale
- Intentional spacing on a 4/8px grid; negative space is a deliberate element
- Restrained palettes with sharp contrast over saturation
- Editorial-grade imagery treated as content (not stock decoration)
- Motion that enhances meaning — one orchestrated page-load + scroll-tied reveals beats scattered micro-flourishes
- Performance treated as aesthetic — fast LCP and stable CLS *feel* premium

**Out:**
- Gratuitous animation, scroll-jacking, parallax for parallax's sake
- Decorative typography swapped in for missing hierarchy
- Oversaturated gradient soup (especially the lavender-on-white SaaS-template look)
- Generic stock imagery, dead 3D blobs, default emoji icons
- "Looks fine, loads in 8s" designs

## Inspiration Sources (by problem, not by browsing)

When stuck on *how* to solve a specific UI problem, look at how shipped products solved it before designing from scratch. Use as references, not templates:

- **SaaS landing pages** → [saaspo.com](https://saaspo.com), [saaswebsites.com](https://saaswebsites.com), [land-book.com](https://land-book.com), [lapa.ninja](https://lapa.ninja), [landingfolio.com](https://landingfolio.com)
- **Real product UIs / SaaS dashboards** → [mobbin.com](https://mobbin.com), [saasframe.io](https://saasframe.io), [designvault.io](https://designvault.io), [refero.design](https://refero.design), [interface-index.com](https://interface-index.com)
- **Real user flows (onboarding→checkout videos)** → [pageflows.com](https://pageflows.com), [uisources.com](https://uisources.com), [theappfuel.com](https://theappfuel.com)
- **Micro-interactions / detail work** → [designspells.com](https://designspells.com), [60fps.design](https://60fps.design), [detailsmatter.framer.website](https://detailsmatter.framer.website), [nicelydone.club](https://nicelydone.club), [ripplix.com](https://ripplix.com)
- **Dark-mode product UIs** → [darkmodedesign.com](https://darkmodedesign.com), [godly.website](https://godly.website), [awwwards.com](https://awwwards.com)
- **Hero / CTA / nav sub-patterns** → [supahero.io](https://supahero.io), [cta.gallery](https://cta.gallery), [navbar.gallery](https://navbar.gallery)
- **Mobile app UIs** → Mobbin (mobile), [appshots.design](https://appshots.design), [scrnshts.club](https://scrnshts.club), [paywallpro.app](https://paywallpro.app)
- **Award-winning creative web** → [awwwards.com](https://awwwards.com), [thefwa.com](https://thefwa.com), [siteinspire.com](https://siteinspire.com), [hoverstat.es](https://hoverstat.es)
- **Email** → [reallygoodemails.com](https://reallygoodemails.com) · **Data viz** → [datavizproject.com](https://datavizproject.com)

**How to use them:** study the *pattern* (why does that hero feel premium? what's the type rhythm? where's the motion?). Don't pixel-copy. Goal: build a personal visual vocabulary, not a swipe file.

### Anti-Patterns to Avoid
- Generic AI aesthetics: cookie-cutter layouts, predictable component patterns
- Cliched color schemes: lavender-on-white SaaS gradients applied without intent
- Animation libraries when CSS handles it fine
- Tailwind in projects that already have a custom design system
- Custom CSS in Laravel/Tailwind projects
- Adding new CSS variables when existing design tokens fit
- `'use client'` on components that don't need state/interactivity
- Shipping a UI without checking LCP/CLS — slow = ugly in 2026

## Reference docs — load on demand

Four deep-dive references live in `references/`. Read the one you need when a task calls for it — don't load all four up front.

- **`references/design-tokens.md`** — OKLCH color ramps, a three-tier token architecture, a ready-to-drop Tailwind v4 `@theme` block, spacing/type/radii scales, and dark-mode elevation by lightness. Load when setting up a design system or defining tokens.
- **`references/premium-rubric.md`** — the 12-point premium filter (first-600ms, type rhythm, color discipline, layered shadows, focus rings, empty states, the signature detail) plus the named anti-AI-slop FAIL/PASS tells. Load to self-grade a build before shipping.
- **`references/motion-library.md`** — the ease-curve catalog with exact cubic-beziers, durations-by-intent, asymmetric enter/exit rules, copy-paste patterns (hover lift, staggered reveal, modal entry, shimmer), and the `prefers-reduced-motion` block. Load when adding animation or interaction.
- **`references/imagery-and-icons.md`** — the AVIF→WebP→JPEG `<picture>` cascade, `srcset`/`sizes` budgeting, CLS-prevention, hero preload, an icon-library comparison with `currentColor`/ARIA wiring, and OKLCH-based art direction. Load when working with images or icons.

## Implementation Notes

- Read the existing CSS/Blade/component code before writing new code — match conventions
- If the project has a `BRAND_GUIDE.md`, `DESIGN.md`, or similar, read it first
- Performance matters: self-hosted fonts, minimal JS, CSS-only animation where possible
- Reveal/scroll-triggered classes commonly use `opacity: 0` until a `.visible` class is added — never double up the trigger class on both wrapper and child

Remember: Claude is capable of extraordinary creative work. Don't hold back — show what can truly be created when thinking outside the box and committing fully to a distinctive vision. But always respect the project's established patterns.
