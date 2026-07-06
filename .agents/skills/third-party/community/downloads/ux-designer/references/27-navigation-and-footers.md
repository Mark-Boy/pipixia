# Navigation & Footers

The two frame elements every page shares. Strategy and review criteria for the **header** (orient + one action) and the **footer** (safety net + sitemap). Copy-paste CSS for the scroll states, blur, and mega-menu markup lives in the `/frontend-design` skill — this ref owns the *why*, the *when*, and the review bar.

---

## Headers / Navigation

A good header is **slim, high content-to-chrome, and carries only essentials**: logo, primary nav (or one mega-menu), and *one* primary CTA. Everything else is a distraction from the action you want.

### Sizing & content budget
- **Desktop height ≤ ~64px; mobile ≤ ~56–60px.** Anything taller eats the hero and lowers content-to-chrome.
- **One primary CTA, not a row of them.** Decisions cost time (Hick's Law) — every extra header button dilutes the one you care about.
- Logo links home. Nav labels are nouns, short, scannable.

### Scroll-state patterns (pick one, animate cheaply)
- **Sticky (`position: sticky; top: 0`) over `fixed`** for most site headers — keeps normal document flow and performs better. Set `scroll-padding-top` = header height so in-page anchor links don't land *under* the bar.
- **Transparent → solid/blurred on scroll:** header overlays the hero, then gains a solid or `backdrop-filter`-blurred background + subtle shadow after **~100–200px** so text stays legible. Apply the solid state when a mega-menu/dropdown opens, too.
- **Shrink-on-scroll:** full header collapses to a compact bar past a threshold. Animate **`transform`/`opacity` only** (never `height`/`top` — they thrash layout), **~200–300ms**.
- **Hide-on-scroll-down, reveal-on-scroll-up** (Shopify pattern) — reclaims reading space, best on mobile.
- Subtle shadow appears **only once floating** — not at rest. Motion should be barely noticeable (Apple/Stripe/Linear all do this).

### Mega menus
- For broad product lines (the Stripe pattern): slim bar, rich categorized dropdown on **hover *and* focus** (keyboard parity).
- **Don't cover the whole viewport.** Allow click-outside and `Esc` to dismiss. Animate from the trigger's `transform-origin` so it grows from the button.

### Mobile
- Hamburger → full-screen or slide-in panel. Keep **logo + one CTA** visible behind/above the toggle.
- **Don't trap keyboard focus** behind the closed panel; manage focus into the panel on open and back to the toggle on close.
- **Test with the virtual keyboard open** — mobile nav and any search-in-header break here most often.
- **Never stack two sticky bars** (top header + bottom action bar) on mobile — they eat the small viewport from both ends.

### Accessibility review bar
- Semantic `<header>` and `<nav>`; a **skip-link to `<main>`** as the first focusable element.
- **Visible focus states** on every control; nav controls (hamburger icon, toggles, links) meet **3:1 non-text contrast** (WCAG 1.4.11) against their background. Contrast is the web's #1 a11y failure — low-contrast text was on **83.9%** of home pages in the WebAIM Million 2026 report — so don't let a translucent-on-hero header quietly drop the logo/nav below 3:1 in its transparent state.

### Applying it to a real brand
The portable rule is the *scroll behavior*; the palette and temperature are yours to layer on top. A dark-first surface (e.g. a near-black like `#0a0a0a` with a restrained accent) typically rides transparent over the hero, then settles to a blurred near-black with the accent reserved for the single CTA. A light-first surface (e.g. an off-white like `#fafafa` with one accent) usually reads better solid from the top. Same pattern, opposite temperature — apply your own palette over the same mechanics.

---

## Footers

The footer is **underrated real estate** — a safety net for anyone who scrolled the whole page without finding what they needed. Chartbeat's *Scroll Behavior Across the Web* (25M sessions) found just under **70% of visitors saw the very top** of the page and the most-viewed band is just above the fold — but in related Chartbeat data on 2B visits, **66% of attention on a normal page is spent below the fold**, so deep-scrollers absolutely reach the footer. Treat it as the second-most-considered surface, not an afterthought.

### The fat footer is the default
The **"fat footer" (a.k.a. doormat / mega footer)** is the modern default for content-rich and SaaS sites: a mini-sitemap of grouped links under clear category headers, plus utility. Columns by category — **Product / Solutions / Resources / Company / Legal**.

### What to include
- **Logo + one-line mission** — brand reinforcement, reminds the visitor whose site this is.
- **Grouped navigation** — the mini-sitemap above.
- **One primary CTA** — newsletter signup *or* "Get started," not five competing asks.
- **Contact / address** — trust signal *and* local-SEO value. NAP (name/address/phone) consistency feeds Google Business Profile and local-pack ranking, so a physical address in the footer is cheap, durable local SEO for any business with a location.
- **Social icons live here, not in the header** — putting them up top bleeds traffic out before the visitor reads anything.
- **Legal** — Privacy, Terms — and **accessibility/status** links.

### Patterns by site type
- **Fat / doormat** — large sites, multi-service: the full grouped sitemap. Default for most SaaS and content-rich marketing sites.
- **Minimal** — simple/one-page sites: copyright + a handful of links.
- **CTA footer** — landing pages: one focused action, nothing to compete with it.
- **Mega footer** — marketplaces: can fold in search, maps, location pickers.

### Design treatment & review bar
- **Clear hierarchy: bold category headers, normal-weight sub-links.** NN/g specifically warns against the unstructured "dumping ground" of orphan links — grouping under headers is what makes a fat footer scannable instead of a wall.
- Short, scannable labels; generous spacing; the footer gets the same 8pt rhythm as the rest of the page.
- **Distinct background** — a dark or tinted surface to separate it from content. A dark-first page may already end on its near-black field; a light-first page should drop to a deep or tinted footer for the same separation.
- **Same performance care as anything else:** lazy-load heavy social embeds, status widgets, and map iframes — don't tank a clean LCP/CLS score at the bottom of the page.

---

## Quick review checklist

**Header**
- [ ] ≤64px desktop / ≤56–60px mobile; one primary CTA only
- [ ] Sticky (not fixed) with `scroll-padding-top` = header height for anchors
- [ ] Transparent→solid only kicks in after ~100–200px; logo/nav clear 3:1 in *both* states
- [ ] Scroll animations touch `transform`/`opacity` only, ≤300ms
- [ ] Skip-link first, semantic `<header>`/`<nav>`, visible focus, keyboard-operable menus
- [ ] Mobile panel doesn't trap focus; tested with the virtual keyboard; no double sticky bars

**Footer**
- [ ] Grouped under bold category headers — no orphan-link dump
- [ ] Logo + mission, one CTA, contact/address, legal + a11y/status links
- [ ] Social icons here, not the header
- [ ] Distinct (dark/tinted) background; heavy embeds lazy-loaded
