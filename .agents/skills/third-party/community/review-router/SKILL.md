---
name: code-review-router
description: Intelligently routes code reviews between Claude Opus, Sonnet, and Haiku models based on tech stack, complexity, and change characteristics. Use when you want an automated code review of your current changes.
---

# Code Review Router

Routes code reviews to the optimal Claude model (Opus, Sonnet, or Haiku) based on change characteristics.

**Available Models:**
- **Opus** — Most capable. Use for complex, security-sensitive, or architecturally significant changes.
- **Sonnet** — Balanced. Use for moderate complexity, multi-file changes, and general-purpose reviews.
- **Haiku** — Fastest. Use for simple, small, low-risk changes like styling, docs, or single-file fixes.

## When NOT to Use This Skill

- For non-code reviews (documentation proofreading, prose editing)
- When reviewing external/third-party code you don't control
- For commit message generation (use a dedicated commit skill)
- When the user requests a specific model (use that model directly)

## Step 0: Environment Check

Verify we're in a git repository:

```bash
git rev-parse --git-dir 2>/dev/null || echo "NOT_A_GIT_REPO"
```

**If not a git repo:** Stop and inform the user: "This directory is not a git repository. Initialize with `git init` or navigate to a repo."

## Step 1: Analyze Git Diff

Run these commands to gather diff statistics:

```bash
# Get diff stats (staged + unstaged)
git --no-pager diff --stat HEAD 2>/dev/null || git --no-pager diff --stat

# Get full diff for pattern analysis
git --no-pager diff HEAD 2>/dev/null || git --no-pager diff

# Count changed files
git --no-pager diff --name-only HEAD 2>/dev/null | wc -l

# Count total changed lines
git --no-pager diff --numstat HEAD 2>/dev/null | awk '{added+=$1; removed+=$2} END {print added+removed}'
```

**If no changes detected:** Report "Nothing to review - no uncommitted changes found." and stop.

## Step 2: Calculate Complexity Score

Initialize `complexity_score = 0`, then add points:

| Condition | Points | Detection Method |
|-----------|--------|------------------|
| Files changed > 10 | +2 | `git diff --name-only \| wc -l` |
| Files changed > 20 | +3 | (additional, total +5) |
| Lines changed > 300 | +2 | `git diff --numstat` sum |
| Lines changed > 500 | +3 | (additional, total +5) |
| Multiple directories touched | +1 | Count unique dirs in changed files |
| Test files included | +1 | Files matching `*test*`, `*spec*` |
| Config files changed | +1 | Files: `*.config.*`, `*.json`, `*.yaml`, `*.yml`, `*.toml` |
| Database/schema changes | +2 | Files: `*migration*`, `*schema*`, `*.sql`, `prisma/*` |
| API route changes | +2 | Files in `api/`, `routes/`, containing `endpoint`, `handler` |
| Service layer changes | +2 | Files in `services/`, `*service*`, `*provider*` |

## Step 3: Detect Language & Framework

Analyze file extensions and content patterns:

### Primary Language Detection
```
.ts, .tsx     → TypeScript
.js, .jsx     → JavaScript
.py           → Python
.go           → Go
.rs           → Rust
.java         → Java
.rb           → Ruby
.php          → PHP
.cs           → C#
.swift        → Swift
.kt           → Kotlin
```

### Framework Detection (check imports/file patterns)
```
React/Next.js    → "import React", "from 'react'", "next.config", pages/, app/
Vue              → ".vue" files, "import Vue", "from 'vue'"
Angular          → "angular.json", "@angular/core"
Django           → "django", "models.py", "views.py", "urls.py"
FastAPI          → "from fastapi", "FastAPI("
Express          → "express()", "from 'express'"
NestJS           → "@nestjs/", "*.module.ts", "*.controller.ts"
Rails            → "Gemfile" with rails, app/controllers/
Spring           → "springframework", "@RestController"
```

### Security-Sensitive Patterns

Detect by **file path** OR **code content**:

**File paths:**
```
**/auth/**
**/security/**
**/*authentication*
**/*authorization*
**/middleware/auth*
```

**Code patterns (in diff content):**
```
password\s*=
api_key\s*=
secret\s*=
Bearer\s+
JWT
\.env
credentials
private_key
access_token
```

**Config files:**
```
.env*
*credentials*
*secrets*
*.pem
*.key
```

## Step 4: Apply Routing Decision Tree

**Routing Priority Order** (evaluate top-to-bottom, first match wins):

### Priority 1: Pattern-Based Rules (Hard Rules)

| Pattern | Model | Reason |
|---------|-------|--------|
| Security-sensitive files/code detected | **Opus** | Requires careful security analysis |
| Files > 20 OR lines > 500 | **Opus** | Large changeset needs thorough review |
| Database migrations or schema changes | **Opus** | Architectural risk |
| API/service layer modifications | **Opus** | Backend architectural changes |
| Changes span 3+ top-level directories | **Opus** | Multi-service impact |
| Complex TypeScript (generics, type utilities) | **Opus** | Type system complexity |
| Multi-file changes (5-20 files) | **Sonnet** | Moderate scope, balanced analysis |
| Test file additions/modifications | **Sonnet** | Test logic needs careful review |
| Config file changes (non-security) | **Sonnet** | Moderate risk, need correctness check |
| Refactoring (renames, restructuring) | **Sonnet** | Needs context-aware review |
| Pure frontend only (jsx/tsx/vue/css/html) | **Haiku** | Simpler, visual-focused review |
| Documentation only (md/txt/rst) | **Haiku** | Simple text review |
| Single file, < 50 lines changed | **Haiku** | Small, low-risk change |
| Style/formatting only changes | **Haiku** | Trivial review |

### Priority 2: Complexity Score (if no pattern matched)

| Score | Model | Reason |
|-------|-------|--------|
| >= 7 | **Opus** | High complexity warrants deepest analysis |
| 4 - 6 | **Sonnet** | Moderate complexity, balanced depth and speed |
| < 4 | **Haiku** | Low complexity, prefer speed |

### Priority 3: Default

→ **Sonnet** (best balance of capability and speed for unclear cases)

## Step 5: Execute Review

### Explain Routing Decision

Before executing, output:

```
## Code Review Routing

**Changes detected:**
- Files: [X] files changed
- Lines: [Y] lines modified
- Primary language: [language]
- Framework: [framework or "none detected"]

**Complexity score:** [N]/10
- [List contributing factors]

**Routing decision:** [Opus/Sonnet/Haiku]
- Reason: [primary reason for choice]

**Executing review...**
```

### Determine Execution Strategy

Before launching a subagent, check whether the current session's model matches the routing decision:

- **If routing to the same model family as the current session** (e.g., session is Opus and routing decision is Opus): **Perform the review directly** in the current context. Do NOT spawn a subagent — it's redundant, adds latency, and may fail due to model version availability mismatches.
- **If routing to a different model** (e.g., session is Opus but routing decision is Haiku): Use the Agent tool to launch a review subagent with that model.

> **Why?** The Agent tool's `model` parameter resolves to whichever version the system provides. This may differ from the session's model version and can fail if that version is unavailable. The current session's model is always available.

### Execute Review

**If performing directly (same model):**

Review the diff using the review prompt below. No subagent needed.

**If using a subagent (different model):**

Use the Agent tool to launch a review subagent:

**Agent tool parameters:**
- `subagent_type`: `"general-purpose"`
- `model`: `"opus"` | `"sonnet"` | `"haiku"` (based on routing decision)
- `prompt`: Include the full diff and the review instructions below

**Review prompt template:**
```
Review the following code diff. Provide specific, actionable feedback organized by:

1. **Critical Issues** — Bugs, security vulnerabilities, data loss risks
2. **Code Quality** — Best practices violations, maintainability concerns
3. **Performance** — Inefficiencies, unnecessary allocations, N+1 queries
4. **Suggestions** — Improvements that would make the code better but aren't blocking

For each finding, reference the specific file and line. If the change looks good, say so briefly.

Diff:
[INSERT FULL DIFF HERE]
```

## Step 6: Handle Failures with Fallback

If a subagent fails or returns an empty response (0 tokens):

1. **Report the failure:**
   ```
   Review with [Model] failed: [error message]
   Falling back...
   ```

2. **Fallback strategy** (in priority order):
   - **First:** Fall back to the current session's model (perform review directly, no subagent). This is always available since it's the model running the skill.
   - **Then:** If the current session model also doesn't produce a good review, try the next model in the chain: Opus → Sonnet → Haiku.

3. **If all fail:**
   ```
   All review models failed. Please check your Claude Code configuration and try again.
   ```

## Step 7: Format Output

Present the review results clearly:

```
## Code Review Results

**Reviewed by:** Claude [Opus/Sonnet/Haiku]
**Routing reason:** [brief reason]

---

[Review output here]

---

**Review complete.** [X files, Y lines analyzed]
```

## Quick Reference

| Change Type | Model | Reason |
|-------------|-------|--------|
| Single typo fix | Haiku | Trivial change |
| CSS/styling update | Haiku | Pure frontend |
| Documentation edits | Haiku | Simple text |
| React component styling | Haiku | Pure frontend |
| Django view update | Sonnet | Moderate backend logic |
| Multi-file refactor (< 20 files) | Sonnet | Moderate scope |
| Test suite additions | Sonnet | Test logic review |
| Config/CI changes | Sonnet | Moderate risk |
| New API endpoint + tests | Opus | Architectural |
| Auth system changes | Opus | Security-sensitive |
| Database migration | Opus | Schema change |
| Multi-service refactor (20+ files) | Opus | High complexity |
| TypeScript type overhaul | Opus | Complex types |
