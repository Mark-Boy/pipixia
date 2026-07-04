# Claude Code Review Router

Intelligently routes code reviews between Claude Opus, Sonnet, and Haiku models based on tech stack, complexity, and change characteristics. Use when you want an automated code review of your current changes.

## Usage

### Install

Clone or copy this repo into your Claude Code skills directory:

```bash
# Global install (available in all projects)
cp -r . ~/.claude/skills/code-review-router

# Project-level install (available only in current project)
cp -r . .claude/skills/code-review-router
```

### Run

In Claude Code, invoke the skill with:

```
/code-review-router
```

The skill will automatically:

1. Detect uncommitted changes in your git repo
2. Analyze complexity, language, framework, and security patterns
3. Route the review to the optimal Claude model (Opus, Sonnet, or Haiku)
4. Return structured feedback organized by severity

### Routing Overview

| Change Type | Model | Why |
|---|---|---|
| Auth/security changes, large diffs, DB migrations | **Opus** | Needs deep analysis |
| Multi-file refactors, tests, config changes | **Sonnet** | Balanced depth and speed |
| Docs, styling, single small file changes | **Haiku** | Fast, low-risk review |

## Credits

Modified from [agent-skills-code-review-router](https://github.com/win4r/agent-skills-code-review-router) by [win4r](https://github.com/win4r). The original skill routes code reviews to external tools (Gemini CLI and Codex CLI). This version is adapted for Claude Code, routing reviews across Claude's own model family (Opus, Sonnet, and Haiku) instead.

## License

[MIT](LICENSE)
