# Premium Rubric — what separates premium work from generic

Use this checklist BEFORE shipping any client-facing surface. Anything failing more than 3 boxes is not premium yet — keep working.

## The 12-point premium filter

### 1. The first 600ms feel earned
- LCP under 1.5s on mid-tier hardware
- No layout shift after first paint (CLS < 0.05)
- Fonts swap-in without FOUT/FOIT — `font-display: swap` + size-adjust descriptors when needed
- Hero image (if any) is dimensioned (width/height attrs) so reserved space is correct

### 2. Type rhythm is deliberate
- Display headline uses a different family than body (e.g., Space Grotesk + Inter, Söhne + Cabinet, GT Sectra + Inter)
- Tracking on display: `-.018em` to `-.025em` (never default 0)
- Line-height on body: 1.55–1.7 (never default 1.2)
- Optical sizing where supported: `font-optical-sizing: auto`
- Numbers tabular when in tables: `font-variant-numeric: tabular-nums`
- Max 3 sizes per surface (display / body / micro)

### 3. Spacing is on a scale, not vibes
- 4 or 8px grid; every margin / padding / gap is a multiple
- Section rhythm: vertical space between sections > vertical space within sections (typical: 80px between, 24-32px within)
- Cards have generous internal padding (24px+) — cramped padding screams template

### 4. Color discipline
- Max 1 brand color + neutrals + 3 semantic states (success/warning/danger)
- Background is not pure `#fff` — use `#fafafa`/`#f8fafc` (warm/cool off-white) for surface depth
- Dark mode bg is not pure `#000` — use `#0a0a0a`/`#111114` (eye fatigue)
- Borders are subtle — `rgba(0,0,0,.06)` or zinc-200, not stark `#ccc`

### 5. Shadows are layered
- One shadow = flat. Two shadows minimum = depth.
- Standard recipe: tight ambient + soft elevation:
  ```css
  box-shadow:
    0 1px 2px rgba(0,0,0,.04),
    0 1px 3px rgba(0,0,0,.06);
  ```
- Premium card hover gets a third layer (lift):
  ```css
  box-shadow:
    0 1px 2px rgba(0,0,0,.04),
    0 8px 24px -8px rgba(99,102,241,.18),
    0 4px 12px -2px rgba(0,0,0,.06);
  ```

### 6. Radii are intentional
- One scale (e.g., 6/10/14/20px). Mixing arbitrary radii feels amateur.
- Cards 12–16px, buttons 8–10px, pills 999px, chips 9–12px.

### 7. Motion is curated
- Not Material-default linear / ease. Use `cubic-bezier(.16, 1, .3, 1)` for outgoing, `cubic-bezier(.34, 1.56, .64, 1)` for spring entries.
- Durations: 120ms feedback, 240ms most transitions, 400ms emphasis, 600ms only for hero reveals.
- `prefers-reduced-motion: reduce` short-circuits to opacity-only.
- Hover lifts under 100ms; press-down feedback is the ONLY case for shorter.

### 8. Focus rings are designed
- Default browser ring = amateur. Use:
  ```css
  outline: none;
  box-shadow: 0 0 0 3px rgba(<accent>, 0.18);
  ```
- Or 2px accent ring with 1px offset white between for double-contrast on busy surfaces

### 9. Forms feel premium
- Inputs are 12–14px vertical padding, 14–15px horizontal
- Border `1px solid <line-strong>` (not `<line>` — needs visible weight)
- Focus → accent border + soft ring, no blue browser default
- Placeholder is true `--dim` (not gray-200 invisible mush)
- Labels above field, 13px, weight 500
- Errors inline below field with subtle red panel — never alert()

### 10. Empty states sell
- Never an empty page. Even "no items yet" shows what's possible
- Soft icon in a colored circle ≠ stock SVG dumped at 24px
- One clear action below the message
- A small empty-state pattern library pays for itself across a product

### 11. Copy is concise and confident
- Headlines are declarative ("Welcome back." not "Welcome back to your account!")
- No exclamation points except in success states
- No "kindly," "please note," "thank you for your patience"
- Microcopy explains the constraint not the obvious ("Links expire in 15 minutes." not "Click the button to send.")
- See `../../ux-designer/references/09-ux-writing.md` for full voice patterns

### 12. The detail nobody asks for
- One signature detail per surface — the thing that makes it memorable. Examples:
  - An eyebrow rule that flanks a section pill
  - An avatar that's filled-accent when staff replies vs neutral when the customer does
  - A subtle aurora gradient in the auth page background
  - A chevron that appears only on row hover
- Without this detail, the work is competent. With it, it's premium.

## The anti-AI-slop filter — named FAIL signals

If a surface ships any of these, it reads as AI/template default. These are the exact tells the 2025/2026 backlash is reacting to — the differentiator now is human craft, not another mesh gradient.

**FAIL signals (each is a hard tell):**
- **The "Tech Bro Gradient"** — purple→blue mesh blob on a near-black background (OpenAI/Anthropic/Midjourney-derived, now everywhere on ProductHunt). This is the single most over-used AI look.
- **The identical centered hero** — big "Reimagine the future" headline + a gradient blob + two buttons, centered. Every vibe-coded landing page is this exact layout.
- **Heavy glassmorphism everywhere** — frosted blur on every card/panel instead of as a single deliberate accent.
- **Default Lucide-on-everything** — Lucide is excellent, but baked into AI/templates; the unmodified Lucide set reads as generic. Same caution for Heroicons. (Phosphor / Tabler / Iconoir / Hugeicons buy distinctiveness — see the `../../ux-designer` icon notes.)
- **Generic stock photos and "suspiciously smooth" AI illustration** — the too-perfect generative-illustration style signals "template" instantly.

**PASS criteria (the positive counter-rule):**
- **Near-neutral foundation + ONE disciplined accent** — the Linear/Stripe/Vercel model. Neutrals dominate (60-30-10); the brand color is the 10% splash, not the surface. Reference accents used with restraint: Stripe "blurple" `#635BFF`, Linear indigo `#5E6AD2`, Raycast red `#FF6363`.
- **Non-default accent hue + unexpected neutral temperature** — pick a hue that isn't indigo/purple, and warm or cool your off-blacks/off-whites (navy, warm charcoal) instead of #000/#fff. In OKLCH you change *one number* (the hue) to make the whole ramp yours.
- **One distinctive / custom-feeling type choice** — a characterful display face or a quality variable workhorse used with strong weight contrast. Custom or carefully-chosen type is the moat (Vercel commissioned Geist, Stripe commissioned Söhne, Mercury commissioned Arcadia and chose purple specifically to break the fintech blue/green default).
- **Real product UI over abstract decoration** — show the product working; near-universal 2026 pattern. Real screenshots beat a gradient blob every time.

**Nuance — dark-mode + one neon accent is ITSELF now a cliché** ("the new 'blue for trust'"). Take the *principles* — contrast, whitespace, restraint, custom-feeling type, real imagery — not the dark-purple surface. Copying the surface is how you end up back in the slop.

**When a real brand owns a specific look, that's not the tell.** A deliberate, owned system — say, a dark-first surface with a consistent two-color accent, a committed type pairing, and glass cards used with intent — is a brand, not slop. The tell is the *generic* purple-on-white / purple→blue Tech-Bro template look applied with no point of view. Flag the template, never a real palette someone chose and committed to.

## Quick triage when reviewing existing work

Look at the surface for 5 seconds. Ask:
1. Could this have been generated by any AI in 30 seconds? → not premium yet
2. Does a specific detail catch your eye? → getting there
3. Does the typography breathe? Or is it cramped?
4. Are shadows layered or flat?
5. Is there a single disciplined accent used consistently, or a Tech-Bro-Gradient "purple gradient soup"? (See the anti-AI-slop filter above for the named tells.)
6. Are focus states designed or default?

If unsure: open the screenshot next to Linear's, Stripe's, or Vercel's equivalent surface. If yours looks like a template and theirs looks like a product, you're not done.
