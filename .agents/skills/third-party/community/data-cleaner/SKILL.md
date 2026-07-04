---
name: data-cleaning
description: Clean dirty CSV/TSV data using a fast Zig CLI. Handles BOM, mixed line endings, whitespace, duplicates, empty rows, smart quotes, null tokens, type detection, outlier detection (IQR/zscore), missing-value imputation, and column-level validation with optional strict-mode CI gating. Use when the user has a CSV/TSV they want to inspect, normalize, dedupe, validate, or run an outlier audit on, and prefers a single command-line pass over writing pandas/awk one-offs.
version: 1.1.0
tools: Bash, Read, Write
---

# data-cleaning

A self-contained data cleaning toolkit built around a Zig binary, `dataclean`, that reads CSV/TSV from a file or stdin and writes a cleaned version to stdout (or `--output FILE`). All pipeline operations are opt-in via flags so the skill is non-destructive by default.

## When to use this skill

- The user provides a CSV/TSV and asks to clean, dedupe, normalize, or audit it.
- The user wants a profile of an unfamiliar dataset (column types, outliers, basic stats) before deciding what to do with it.
- The user wants column-level validation (`required`, regex, numeric range, enum) as an audit gate before a data load.
- The user wants a Unix-pipeline-friendly tool (`cat foo.csv | dataclean ... | other-tool`).

Do **not** use this skill for:

- JSON, YAML, Parquet, Excel — only delimited text. (The bundled `fixtures/dirty.json` is for round-trip testing of the schema, not parsing.)
- Statistical modeling beyond mean / IQR / z-score outlier flagging.
- Full Unicode normalization (only ASCII-safe transforms are implemented; smart-quote conversion is supported).

## Setup

Build the binary once:

```bash
cd $SKILL_DIR     # the directory containing SKILL.md
bash scripts/install.sh
```

Optionally install to a `PATH` location:

```bash
PREFIX=$HOME/.local bash scripts/install.sh
```

The skill needs Zig 0.15.2+ on `PATH`. The binary is `~338 KB`, has no runtime dependencies, and works on macOS / Linux.

After build, the executable lives at `zig-out/bin/dataclean`. Throughout this document, `dataclean` refers to that path.

## CLI summary

```
dataclean [OPTIONS] [INPUT]
```

- `INPUT` is a path. Omit or pass `-` to read stdin.
- Output goes to stdout unless `--output FILE` is given.
- All reports (`--detect-types`, `--outliers`, `--stats`, validation failures) are written to stderr, never mixed into the cleaned data on stdout.

### Flags (canonical list)

| Flag | Effect |
|------|--------|
| `--trim` | Trim leading/trailing whitespace from each cell. |
| `--collapse-ws` | Collapse internal runs of whitespace to a single space. |
| `--strip-bom` | Strip a leading UTF-8 BOM if present. |
| `--normalize-eol` | Convert CR / CRLF line endings to LF. |
| `--strip-control` | Remove ASCII control bytes (preserving tab). |
| `--smart-quotes` | Convert curly quotes (U+2018/19/1C/1D) to straight ASCII. |
| `--lowercase` | Lowercase ASCII letters in cells. |
| `--drop-empty` | Drop rows whose cells are all empty / whitespace. |
| `--dedupe` | Drop duplicate rows (after other transforms). |
| `--normalize-nulls` | Replace recognized null tokens with empty string. |
| `--null-tokens=A,B,C` | Override default null-token set. Defaults: `"" NA N/A null NULL - ?` |
| `--fill-na=zero\|mean\|drop` | After normalization: fill empty cells with 0 or column mean, or drop the row. |
| `--detect-types` | Profile each column's type (int / float / bool / string / mixed). Reports to stderr. |
| `--outliers=iqr\|zscore` | Flag numeric outliers. Reports to stderr. |
| `--outlier-k=N` | k for IQR (default 1.5) or threshold for z-score (default 3.0). |
| `--validate=COL:RULE` | Audit-only validation. RULE: `required`, `range=LO..HI`, `regex=PAT`, `enum=A,B,C`. Repeatable. |
| `--all` | Bundle: trim, collapse-ws, strip-bom, normalize-eol, strip-control, smart-quotes, drop-empty, dedupe, normalize-nulls. |
| `--delimiter=C` | Field delimiter (default `,`). |
| `--no-header` | Treat first line as data. |
| `--output=FILE` | Write to FILE instead of stdout. |
| `--stats` | Print summary stats to stderr. |
| `--strict` | Exit code 1 if any validation rule fails (use as a CI gate). |
| `--version`, `--help` | Self-explanatory. |

## How to use the skill

1. **Inspect first.** Before mutating anything, run an audit:
   ```bash
   dataclean --detect-types --outliers=iqr --stats <input>
   ```
   This is read-only — no `--output`, no transformative flags, so the file is untouched. Read the stderr report and decide which cleanup steps the data actually needs.

2. **Apply targeted cleanup.** Pick only the flags you need based on the audit. For a generic "Excel-exported" CSV, `--strip-bom --normalize-eol --trim --collapse-ws` is usually enough. For a bulk dataset with duplicates and blanks, `--all` is the safe bundle.

3. **Validate when loading.** When the user is preparing data for an import, add `--validate=` rules. Validation never drops rows; it reports failures to stderr. Add `--strict` to make the binary exit code 1 on any validation failure — useful in CI / data-load scripts.

4. **Atomic in-place writes.** There is no `--in-place` flag. Use `--output foo.tmp && mv foo.tmp foo`.

5. **Reading reports.** Reports go to **stderr** so stdout is always clean CSV. When you want to pipe into another tool, redirect stderr to a log file:
   ```bash
   dataclean --all --stats input.csv 2>report.log | other-tool
   ```

## Recipes

For canned recipes (Excel cleanup, validation gate, TSV, headerless input, etc.), see `references/recipes.md`. Quote the command verbatim — the recipes were written against this exact flag set.

## Reference docs in this skill

- `references/operations.md` — the design rationale and algorithm notes for each cleaning operation. Read this when the user asks "why does it do X" or wants to understand a tradeoff (e.g. how IQR fences are computed, what counts as a default null token).
- `references/recipes.md` — copy-pasteable command recipes for common scenarios.
- `references/zig_idioms.md` — Zig 0.15.2 stdlib idioms used in the implementation. Useful only if you are extending the binary itself.
- `fixtures/dirty.csv`, `fixtures/dirty.csv.expected.txt`, `fixtures/dirty.json`, `fixtures/simple.csv` — test data for verifying changes.

## Verifying the skill works

The skill ships with a full test runner:

```bash
bash scripts/test.sh
```

This runs `zig build test` (11 unit tests covering BOM stripping, EOL normalization, CSV parsing including quoted/embedded-newline fields, transformCell, type detection, percentile, mean / stddev, row hashing, and CSV writing) plus 16 end-to-end shell assertions on the release binary.

Manual smoke test:

```bash
./zig-out/bin/dataclean --all --detect-types --outliers=iqr --stats fixtures/dirty.csv > /tmp/clean.csv 2> /tmp/report.log
cat /tmp/report.log
wc -l /tmp/clean.csv     # should be 27 (1 header + 26 unique data rows)
```

Expected stderr report:

```
# column types
  col[0=id] integer
  col[1=name] string
  col[2=email] string
  col[3=age] integer
  col[4=score] string         # mixed because of "high" / "n/a" rows
  col[5=country] string
  col[6=note] string
# outlier report (method=iqr, k=1.5)
  col[3=age] IQR ... outliers=1
  col[4=score] IQR ... outliers=2
# stats
  rows out: 26
```

## Limitations (1.0)

- Single-byte delimiters only (`--delimiter=,` / `\t`). No multi-byte or regex delimiters.
- Regex validation is a substring/literal match, not a full regex engine. Use `regex=@` to require an `@` somewhere in the cell.
- `--fill-na=mean` falls back to `0` for non-numeric columns. If you want surgical control over a single column's fill, pre-filter the file with `awk` / `cut` first.
- Validation rules report failures but never drop rows. Use `--fill-na=drop` if you need empty-cell rows removed.
- No streaming for huge files: the whole input is loaded into memory. Hard ceiling is 1 GiB per file.

## Changelog

- **1.1.0** — added `--strict` flag (exit 1 on validation failure) and a full test suite (`zig build test` + `scripts/test.sh`).
- **1.0.0** — initial release: full pipeline of cleaning operations, type detection, outlier reporting (IQR / z-score), four validation rule types, fill-na strategies, custom delimiter, optional file output.
