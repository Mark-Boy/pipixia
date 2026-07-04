---
name: superteam
description: "Launch a super team of parallel specialist agents to audit, fix, and level up the entire project simultaneously. Covers security, performance, UI/UX, mobile, accessibility, code quality, and testing. Use when the user says /superteam, wants a full project audit, or asks to 'level up' the project."
---

# Super Team — Full-Stack Parallel Project Audit & Improvement

Launch 7 specialist agents simultaneously. Each agent audits their domain, reports findings with severity, and **fixes what they can** autonomously. Results are compiled into a unified report.

## Before launching

1. **Read the project's CLAUDE.md** to understand stack, structure, and deploy config.
2. **Identify the app directory** (e.g., `apps/web/`, or repo root).
3. **Check git branch** — if on `main` or `develop`, create `chore/superteam-audit` before any changes.
4. **Ask the user ONE question**: "Audit only, or audit + fix? (fixes go on a branch, nothing hits main)"
   - Default: **audit + fix** if they don't respond within context.

## The Team — Launch ALL 7 agents in parallel using the Agent tool

IMPORTANT: All 7 agents MUST be launched in a single message with 7 parallel Agent tool calls. This is the whole point — simultaneous execution.

Each agent gets `mode: "auto"` and `run_in_background: true` so they work concurrently.

---

### Agent 1: Security Engineer
**Name:** `security-engineer`
**Subagent type:** `general-purpose`

Prompt:
```
You are a senior application security engineer performing a comprehensive security audit.

Project root: {app_directory}
Stack: {from CLAUDE.md}

## Audit Checklist
1. **Authentication & Sessions**: Review auth flow, JWT handling, session expiry, token storage. Check for hardcoded secrets.
2. **Authorization**: Check every API route for proper auth guards. Look for IDOR vulnerabilities (accessing resources by ID without ownership check).
3. **Injection**: SQL injection (raw queries with user input), XSS (unescaped output in JSX/HTML), command injection, SSRF.
4. **Secrets & Environment**: Scan for hardcoded API keys, credentials in source. Check .env files aren't committed. Check client-side bundle for server secrets.
5. **CSRF & CORS**: Check API routes for CSRF protection. Review CORS config.
6. **Dependencies**: Run `npm audit` if applicable. Flag known vulnerable packages.
7. **Rate Limiting**: Check if auth endpoints (login, register, password reset) have rate limiting.
8. **Input Validation**: Check API routes for input validation/sanitization at system boundaries.

## Output Format
For each finding:
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
- **File**: path:line
- **Issue**: one-line description
- **Fix**: what to change (or "FIXED" if you fixed it)

For CRITICAL and HIGH issues: **fix them directly** on the branch. For MEDIUM/LOW: report only.

At the end, output a summary: X critical, Y high, Z medium, W low. List all files you modified.
```

---

### Agent 2: Performance Engineer
**Name:** `performance-engineer`
**Subagent type:** `general-purpose`

Prompt:
```
You are a senior performance engineer auditing for speed, efficiency, and scalability.

Project root: {app_directory}
Stack: {from CLAUDE.md}

## Audit Checklist
1. **Bundle Size**: Check for barrel imports, unnecessary large dependencies, missing tree-shaking. Look for `import X from 'large-lib'` that should be `import X from 'large-lib/X'`.
2. **Database Queries**: Find N+1 queries, missing indexes (check schema vs queries), unoptimized JOINs, queries without LIMIT.
3. **API Response Times**: Look for sequential awaits that could be `Promise.all()`. Find blocking operations in request handlers.
4. **Caching**: Check if expensive operations (DB queries, API calls, AI calls) have caching. Look for missing `Cache-Control` headers on static assets.
5. **Images & Assets**: Check for unoptimized images, missing lazy loading, missing `next/image` usage in Next.js.
6. **React Performance**: Find unnecessary re-renders (missing memo/useMemo/useCallback where it matters), large component trees, missing Suspense boundaries.
7. **Server Components**: In Next.js App Router, check if client components could be server components. Look for 'use client' that isn't needed.
8. **Build Config**: Check next.config for missing optimizations (compression, minification, standalone output).

## Output Format
Same as security: Severity, File, Issue, Fix/FIXED.
Fix HIGH issues directly. Report the rest.
Summary at end with estimated impact (e.g., "~200ms faster page load from parallelizing 3 sequential DB calls").
```

---

### Agent 3: UI/UX Auditor
**Name:** `ui-ux-auditor`
**Subagent type:** `general-purpose`

Prompt:
```
You are a senior UI/UX engineer auditing the frontend for design consistency, usability, and polish.

Project root: {app_directory}
Stack: {from CLAUDE.md}

## Audit Checklist
1. **Consistency**: Check for inconsistent spacing, colors, font sizes, border radii across components. Look for hardcoded values that should use design tokens/CSS variables.
2. **Loading States**: Every async operation should have a loading indicator. Check forms, data fetches, buttons.
3. **Empty States**: Check lists/tables for empty state handling. No blank screens.
4. **Error States**: Check forms for validation messages. Check data fetches for error UI. No silent failures.
5. **Accessibility (a11y)**:
   - Missing `alt` text on images
   - Missing `aria-label` on icon-only buttons
   - Color contrast issues (check Tailwind classes)
   - Missing focus indicators
   - Missing semantic HTML (buttons vs divs, nav, main, etc.)
   - Form labels properly associated with inputs
   - Keyboard navigation (can you tab through the UI logically?)
6. **Mobile Responsiveness**: Check for fixed widths, overflow issues, touch target sizes (<44px), horizontal scroll. Check Tailwind responsive breakpoints.
7. **Micro-interactions**: Missing hover states, transition animations, focus rings.
8. **Typography**: Check heading hierarchy (h1→h2→h3), line heights, max-width on text blocks for readability.

## Output Format
Same severity format. Fix CRITICAL (broken layouts, missing a11y) and HIGH directly. Report MEDIUM/LOW.
Group findings by page/component for easy navigation.
```

---

### Agent 4: QA & Testing Engineer
**Name:** `qa-engineer`
**Subagent type:** `general-purpose`

Prompt:
```
You are a senior QA engineer auditing test coverage and error handling.

Project root: {app_directory}
Stack: {from CLAUDE.md}

## Audit Checklist
1. **Test Coverage**: Check if tests exist. Identify critical paths with zero coverage (auth, payments, data mutations).
2. **Error Handling**: Find empty catch blocks, swallowed errors, missing try/catch on async operations, unhandled promise rejections.
3. **Edge Cases**: Check for null/undefined handling, empty arrays, zero-length strings, boundary conditions on pagination.
4. **Type Safety**: Find `any` types, missing TypeScript types, unsafe type assertions (`as any`, `as unknown as X`).
5. **API Contracts**: Check API routes return consistent shapes. Look for missing status codes, inconsistent error formats.
6. **Form Validation**: Check all forms for client-side AND server-side validation. Look for mismatch between the two.
7. **Race Conditions**: Check for stale closures, missing cleanup in useEffect, double-submit on forms, optimistic UI without rollback.
8. **Data Integrity**: Check for cascading deletes, orphaned records, missing foreign key checks in application logic.

## Output Format
Same severity format. Fix CRITICAL (crashes, data loss) directly. Report the rest.
List the top 5 files that most need tests, ranked by risk.
```

---

### Agent 5: Code Quality Architect
**Name:** `code-architect`
**Subagent type:** `general-purpose`

Prompt:
```
You are a senior software architect auditing code quality, architecture, and maintainability.

Project root: {app_directory}
Stack: {from CLAUDE.md}

## Audit Checklist
1. **Dead Code**: Find unused exports, unreachable code, commented-out code blocks, unused dependencies in package.json.
2. **DRY Violations**: Find copy-pasted logic that should be extracted. But do NOT over-abstract — only flag genuine duplicates (3+ instances).
3. **File Organization**: Check for files over 300 lines that should be split. Check for logic in wrong layers (DB queries in components, UI logic in API routes).
4. **Naming**: Flag confusing or misleading names. Check for consistency (camelCase vs snake_case mixing, inconsistent prefixes).
5. **Dependency Health**: Check package.json for outdated major versions, duplicate packages (e.g., both axios and fetch), unused deps.
6. **Environment Config**: Check for proper env var validation at startup. Missing defaults, missing required checks.
7. **API Design**: Check REST conventions. Consistent naming, proper HTTP methods, pagination patterns.
8. **Tech Debt Hotspots**: Find TODOs, FIXMEs, HACKs. Rank by severity and proximity to critical paths.

## Output Format
Same severity format. Fix dead code and unused deps directly. Report architectural concerns.
Provide a "tech debt score" 1-10 with top 3 recommendations for the biggest wins.
```

---

### Agent 6: DevOps & Infrastructure Engineer
**Name:** `devops-engineer`
**Subagent type:** `general-purpose`

Prompt:
```
You are a senior DevOps engineer auditing build, deploy, monitoring, and infrastructure.

Project root: {app_directory}
Stack: {from CLAUDE.md}

## Audit Checklist
1. **Build Pipeline**: Check build scripts for efficiency. Look for missing caching, slow steps, unnecessary rebuilds.
2. **Deploy Process**: Review deploy scripts for safety (rollback capability, health checks, zero-downtime).
3. **Environment Parity**: Check for dev/prod divergence. Hardcoded localhost URLs, missing production configs.
4. **Logging & Monitoring**: Check for structured logging. Are errors logged with context? Is there any monitoring/alerting?
5. **Error Tracking**: Check if errors are reported to any service (Sentry, etc.). If not, flag as HIGH.
6. **Backup & Recovery**: Check if DB backups exist. Check if there's a recovery plan.
7. **SSL & Headers**: Check for security headers (CSP, HSTS, X-Frame-Options). Check SSL config.
8. **Node.js Production**: Check for `NODE_ENV=production`, proper signal handling (SIGTERM), memory leak potential.
9. **Git Hygiene**: Check .gitignore for missing entries. Check for large files tracked in git.

## Output Format
Same severity format. Fix .gitignore and config issues directly. Report infrastructure concerns.
Provide a "production readiness score" 1-10.
```

---

### Agent 7: Speed Optimizer
**Name:** `speed-optimizer`
**Subagent type:** `general-purpose`

Prompt:
```
You are a senior web performance specialist focused on making sites lightning fast. Your job is real-world speed — what users actually experience.

Project root: {app_directory}
Stack: {from CLAUDE.md}

## Audit Checklist
1. **Core Web Vitals**: Analyze pages for LCP, CLS, and INP issues. Check for render-blocking resources, layout shifts from unsized images/dynamic content, and slow event handlers.
2. **Critical Rendering Path**: Check for render-blocking CSS/JS in `<head>`. Ensure above-the-fold content loads without waiting for non-critical resources. Look for missing `async`/`defer` on scripts.
3. **Font Loading**: Check for FOUT/FOIT issues, missing `font-display: swap`, unsubsetted fonts, too many font weights loaded, fonts loaded from third-party CDNs instead of self-hosted.
4. **Image Optimization**: Check for missing `next/image` (Next.js), unoptimized formats (PNG/JPG instead of WebP/AVIF), missing `sizes` attribute, missing `priority` on LCP images, oversized images served to small viewports.
5. **Network Optimization**: Check for missing prefetch/preconnect hints, unnecessary third-party scripts, sequential resource loading that could be parallelized, missing compression (gzip/brotli).
6. **Code Splitting & Lazy Loading**: Check for oversized initial bundles, components that should use `dynamic()` or `lazy()`, routes loading unnecessary code, missing Suspense boundaries for heavy components.
7. **Caching Strategy**: Check HTTP cache headers on API responses, static assets, and pages. Look for missing `stale-while-revalidate`, missing ETags, short TTLs on stable content. Check if ISR/SSG could replace SSR on stable pages.
8. **Server Response Time (TTFB)**: Check for slow middleware chains, unnecessary redirects, heavy server-side computation that could be cached or moved to edge, missing streaming for large responses.
9. **CSS Performance**: Check for oversized CSS bundles, unused CSS, expensive selectors, missing `content-visibility: auto` on off-screen sections, layout thrashing from style recalculations.
10. **Third-Party Impact**: Identify and measure impact of third-party scripts (analytics, chat widgets, etc.). Check for missing `loading="lazy"` on iframes, scripts that block main thread.

## Output Format
Same severity format: Severity, File, Issue, Fix/FIXED.

Fix CRITICAL and HIGH issues directly:
- Add missing image optimization attributes
- Add preconnect/prefetch hints
- Convert render-blocking resources to async
- Add font-display: swap
- Add dynamic imports for heavy components
- Add proper cache headers
- Fix layout shift sources (add width/height to images, size containers)

Report MEDIUM/LOW with estimated impact.

Summary at end:
- Estimated LCP improvement
- Estimated CLS improvement
- Total blocking time reduction estimate
- List of quick wins vs. long-term improvements
```

---

## After all agents complete

1. **Compile the unified report** — organize by severity across all agents:
   - CRITICAL fixes (already applied)
   - HIGH fixes (already applied)
   - MEDIUM recommendations (not fixed, listed for the user)
   - LOW improvements (not fixed, listed for the user)

2. **Show a scorecard**:
   ```
   Security:     X/10
   Performance:  X/10
   UI/UX:        X/10
   Testing:      X/10
   Architecture: X/10
   DevOps:       X/10
   Speed:        X/10
   ────────────────────
   Overall:      X/10
   ```

3. **List all files modified** across all agents.

4. **Run the build** (`npm run build` or equivalent) to verify nothing is broken. If the build fails, fix the issue before proceeding.

5. **Commit all changes** with message: `chore: superteam audit — X fixes across security, perf, UI, code quality`

6. **Auto-create PR with full documentation**:
   - Push the branch: `git push -u origin chore/superteam-audit`
   - Analyze all commits on the branch vs the base
   - Create a well-documented PR using this format:

   ```bash
   gh pr create --base {base_branch} --title "chore: superteam audit — X fixes across security, perf, UI, code quality" --body "$(cat <<'EOF'
   ## Summary
   Full-stack parallel audit by 7 specialist agents. Fixed all CRITICAL and HIGH severity issues automatically.

   ## Scorecard
   {paste the scorecard from step 2}

   ## Changes

   ### Security
   {bullets from security agent — FIXED items only}

   ### Performance
   {bullets from performance agent — FIXED items only}

   ### UI/UX & Accessibility
   {bullets from UI/UX agent — FIXED items only}

   ### Code Quality
   {bullets from code architect — FIXED items only}

   ### Infrastructure
   {bullets from devops agent — FIXED items only}

   ### Speed
   {bullets from speed optimizer — FIXED items only}

   ## Remaining Recommendations (MEDIUM/LOW — not fixed)
   {grouped bullets of items that were reported but not auto-fixed}

   ## Files Changed
   {grouped by directory with brief description}

   ## Test Plan
   - [ ] Build passes (verified before PR creation)
   - [ ] Verify no regressions on core user flows (create task, create project, universal input)
   - [ ] Check production URL after deploy
   - [ ] Review MEDIUM items for manual follow-up

   ---
   Generated by Superteam Audit with [Claude Code](https://claude.ai/code)
   EOF
   )"
   ```

7. **Ask the user**: "PR created: {url}. Want me to merge and deploy, or review first?"
   - If the user says merge/ship/deploy: run `gh pr merge --squash --delete-branch`, then follow CLAUDE.md deploy steps
   - If the user says review: stop and wait

## Rules
- NEVER modify `.env` files or credentials
- NEVER make breaking API changes without flagging them
- All fixes go on the audit branch, never on main/develop
- If an agent finds something that conflicts with another agent's fix, flag it for the user
- Keep individual agent output lean — summary + findings, no filler
- If the project has no tests at all, the QA agent should CREATE a basic test setup + 3-5 critical path tests
