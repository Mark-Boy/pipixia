# Motion Library — when each curve lands premium

Motion is where most "designer-built" interfaces betray themselves. Default `ease` and 300ms `linear` will tank the perception of the whole product. The rules below are stack-agnostic — wire them to whatever token names your project already uses (`--ease-*`, `--shadow-*`, `--bg-*`).

## The four curves and what they're for

### `--ease-out: cubic-bezier(.16, 1, .3, 1)`
**The premium default.** Use for ~80% of transitions.
- Why: starts fast, lands soft. Feels "settled" rather than "abrupt."
- Use for: hover lifts, sidebar slides, accordion opens, modal entries
- Use with: 240ms or 400ms

### `--ease-spring: cubic-bezier(.34, 1.56, .64, 1)`
**The "popping in" curve.** Use for things appearing fresh.
- Why: overshoots slightly then settles. Feels alive without being childish.
- Use for: toast entries, badge appears, item adds to a list, success states
- Use with: 240ms (faster overshoot reads natural; longer feels goofy)

### `--ease-in-out: cubic-bezier(.4, 0, .2, 1)` (Material default)
**Reserved for color and opacity only.** Avoid for transforms.
- Why: feels machine-like on movement; fine for color cross-fades
- Use for: opacity cross-fades between states, background color shifts
- Use with: 160ms or 240ms

### `--ease-linear: linear`
**The "this is information" curve.** Use sparingly.
- Why: feels mechanical, which is correct for loading bars and progress
- Use for: spinner rotation, loading bar fill, scroll-tied animations
- Never use for: anything that moves or scales

### Pick the curve by direction (the asymmetric rule)
Material's durable rule — match the curve to what the element is *doing*:
- **Entering** (modal opens, toast appears, menu expands) → **ease-out** (`--ease-out`). Decelerate into place.
- **Exiting** (dismiss, close, remove) → **ease-in** (`cubic-bezier(.4, 0, 1, 1)`). Accelerate away — and make exits **shorter than entrances** (e.g. enter 240ms / exit 160ms); the user already decided, don't make them wait.
- **Moving on-screen** (reorder, position shift, drawer that's already visible sliding) → **standard/ease-in-out** (`--ease-in-out`). Accelerate out, decelerate in.

So the one curve this file otherwise tells you to avoid for transforms — `cubic-bezier(.4, 0, 1, 1)` — is *correct* on exits, because the element is leaving the screen anyway. The "accelerating into a wall" problem only happens when it lands somewhere you keep looking.

**Spatial continuity:** animate from the trigger. Set `transform-origin` so a dropdown grows from its button, a popover from its anchor, a zoom from the thumbnail. A menu that scales in from `top right` (under the button that opened it) reads connected; one that fades in centered reads disconnected.
```css
.menu { transform-origin: top right; animation: pop-in 200ms var(--ease-out); }
@keyframes pop-in { from { opacity: 0; transform: scale(.96); } to { opacity: 1; transform: scale(1); } }
```

**Budget exception:** the ≤400ms ceiling is for functional UI. **Celebrations may exceed it** — a confetti burst, a success checkmark draw, a first-onboarding flourish can run 600–1200ms because the delight *is* the point. Everything load-bearing stays under budget.

### Avoid
- `cubic-bezier(.4, 0, 1, 1)` (Material acceleration) — feels accelerating into a wall **for entrances and on-screen moves** (it's the right curve on *exits* — see above)
- `cubic-bezier(.68, -.55, .27, 1.55)` (bouncy bounce) — playful only; almost never premium

## Durations by intent

| Intent | Duration | Curve | Example |
|---|---|---|---|
| Press feedback | 80ms | linear | Button color darken on mousedown |
| Hover lift | 160ms | ease-out | Card raises 2px on hover |
| Standard transition | 240ms | ease-out | Most state changes |
| Modal/dialog entry | 320–400ms | ease-out | Sheet slides up |
| Hero reveal | 600ms | ease-out | Landing-page hero fade-in |
| Page transition (route change) | 240ms | ease-out + opacity-only | Don't slide pages — opacity x-fade |

## Patterns that land premium

### Hover lift (cards, list rows)
```css
.card {
    transition: transform 160ms var(--ease-out),
                box-shadow 160ms var(--ease-out);
}
.card:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}
```
**Not** `transform: scale(1.02)` (looks template). **Not** `translateY(-4px)` (too much). 1px lift + shadow upgrade reads premium.

### Press-down feedback
```css
.btn {
    transition: background 240ms var(--ease-out),
                transform 80ms linear;
}
.btn:active {
    transform: translateY(1px);
    transition-duration: 80ms;
}
```

### Staggered list entry (one-shot on mount)
```css
@keyframes rise {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.row {
    animation: rise 400ms var(--ease-out) backwards;
}
.row:nth-child(1) { animation-delay: 0ms; }
.row:nth-child(2) { animation-delay: 60ms; }
.row:nth-child(3) { animation-delay: 120ms; }
.row:nth-child(4) { animation-delay: 180ms; }
.row:nth-child(n+5) { animation-delay: 240ms; }
```
**Stagger no more than 5 items**, then snap-in the rest. 50–60ms between items is the sweet spot.

### Scroll-triggered reveal
```js
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.classList.add('is-visible');
            observer.unobserve(e.target);
        }
    });
}, { threshold: 0.15 });

document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
```
```css
.reveal { opacity: 0; transform: translateY(16px); transition: opacity 600ms var(--ease-out), transform 600ms var(--ease-out); }
.reveal.is-visible { opacity: 1; transform: translateY(0); }
```
Single-use only — don't re-trigger on scroll back. Run once.

### Modal entry
```css
.modal {
    animation:
      modal-fade 200ms var(--ease-out),
      modal-rise 320ms var(--ease-out);
}
@keyframes modal-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes modal-rise { from { transform: translateY(12px); } to { transform: translateY(0); } }
.modal-backdrop { animation: modal-fade 240ms var(--ease-out); }
```

### Skeleton shimmer (loading state)
```css
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.skeleton {
    background: linear-gradient(90deg, var(--bg-subtle) 0%, var(--bg-elev) 50%, var(--bg-subtle) 100%);
    background-size: 200% 100%;
    animation: shimmer 1400ms linear infinite;
}
```
Shimmer is one of the few legitimate uses of `linear`. Speed: 1400ms feels alive without being distracting; faster (800ms) feels twitchy.

## Reduced motion (always)

Every animation must short-circuit when reduced-motion is preferred:
```css
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
```

Opacity changes are still fine under reduced-motion. Avoid `transform`, parallax, scaling. Cross-fades acceptable.

## The Doherty Threshold (latency, not just curves)

Motion polish is wasted if the *system* feels slow. Keep perceived response under **400ms** — below that, users stay in flow; above it, attention wanders and the interaction feels broken. This is about latency, distinct from the transition durations above.

- If a real action can't return in <400ms (network, compute), don't leave dead air — fire **immediate feedback** (button enters loading state, optimistic UI updates, skeleton appears) within ~100ms so the perceived response is instant even when the result isn't.
- A 240ms ease-out on a button whose backing request takes 2s still feels broken. Animate the *acknowledgement*, not just the eventual result.
- Skeletons and progress text (see shimmer above) exist to keep the experience under the threshold when the data can't.

## Anti-patterns

- Scroll-jacking (taking control of the scroll). Always wrong outside experimental art sites.
- Parallax that runs the full page height. Cliché. Use it for ONE element, briefly.
- `transition: all .3s ease` — lazy. Specify properties.
- 800ms+ durations on common interactions (hover, click). Feels sluggish.
- Animating `top`/`left`/`width`/`height` — janky. Animate `transform` and `opacity` only.
- Loading spinners > 3 seconds — replace with skeleton + progress text.
- `will-change` on everything — costs memory; use only on what's currently animating.
