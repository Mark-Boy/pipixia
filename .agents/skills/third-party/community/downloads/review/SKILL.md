---
name: review
description: Quick security and quality review of current changes before deploying. Use when the user says /review or wants a pre-deploy check. Scans diffs for security issues, credential leaks, and code quality problems.
---

# Review — Pre-Deploy Security & Quality Check

Review all pending changes for security vulnerabilities, credential leaks, and quality issues.

## Steps

1. **Gather changes**:
   - `git diff` (unstaged) and `git diff --staged` (staged)
   - If no local changes, diff against the base branch: `git diff main...HEAD` (or `master`)

2. **Security scan** — check the diff for:
   - **Credential leaks**: API keys, passwords, tokens, secrets, `.env` values hardcoded in source
   - **SQL injection**: raw user input in queries without parameterization
   - **XSS**: unescaped user input rendered in HTML/JSX
   - **Command injection**: user input passed to shell commands
   - **IDOR**: missing authorization checks on endpoints that access resources by ID
   - **Debug code**: `var_dump`, `console.log` with sensitive data, `dd()`, leftover `die()` calls
   - **`.env` changes**: flag if `.env` was modified — it should almost never be committed
   - **API key exposure**: LLM API keys (OpenAI, Anthropic), payment keys (Stripe), auth secrets hardcoded in client-side code
   - **Prompt injection**: user input concatenated directly into LLM prompts without sanitization
   - **SSRF**: user-controlled URLs passed to server-side fetch/curl without validation

3. **Quality scan** — check for:
   - Incomplete implementations (TODO/FIXME/HACK comments in new code)
   - Error handling gaps (empty catch blocks, swallowed exceptions)
   - Obvious logic errors
   - Files that look accidentally included (`.DS_Store`, `node_modules`, compiled assets)

4. **Report**:
   - If issues found: list each with file, line, and severity (CRITICAL / WARNING / INFO)
   - If clean: confirm with a one-line "all clear"
   - Keep the report concise — no filler

## Rules
- NEVER modify code during review — only report findings
- Focus on the diff, not the entire codebase
- CRITICAL issues = must fix before deploy (credentials, injection, auth bypass)
- WARNING = should fix (debug code, missing error handling)
- INFO = nice to fix (style, minor improvements)
- Delegate to an Explore agent if the diff is very large (50+ files)
