# data-cleaning

A fast, dependency-free CSV/TSV cleaning tool written in Zig 0.15.2, packaged as a Claude Code skill.

`dataclean` reads delimited text from a file or stdin and writes a cleaned version to stdout (or `--output FILE`). All transformations are opt-in via flags, so it never mutates data unless you ask. Reports (type detection, outlier detection, validation results, summary stats) go to stderr, leaving stdout pure CSV for piping.

```bash
dataclean --all --detect-types --outliers=iqr --stats data.csv > clean.csv 2> report.log
```

## Features

- **Cleaning**: BOM strip, CRLF/CR → LF, whitespace trim, internal whitespace collapse, control-char strip, smart-quote → ASCII conversion, ASCII lowercasing.
- **Row operations**: drop empty rows, dedupe (FNV-1a hash on full row), drop on validation failure (via `--fill-na=drop` for empty-cell rows).
- **Null handling**: configurable null tokens (`""`, `NA`, `N/A`, `null`, `NULL`, `-`, `?` by default), `--fill-na=zero|mean|drop` strategies.
- **Type detection**: per-column profiling (integer / float / boolean / string / mixed) with merging rules.
- **Outlier detection**: IQR fences (default `k=1.5`) and z-score (default threshold 3.0).
- **Validation**: `required`, `range=LO..HI`, `regex=PAT` (substring match), `enum=A,B,C`. Repeatable. Optional `--strict` exits with code 1 on any failure for CI gating.
- **CSV parsing**: RFC-4180-ish — handles quoted fields with embedded commas, embedded newlines, and `""` escapes.
- **Format options**: custom `--delimiter` (e.g. tab for TSV), `--no-header`, `--output FILE`.
- **Streaming-friendly**: reads stdin, writes stdout, so it slots into Unix pipelines.

## Build

Requires Zig 0.15.2 or newer.

```bash
git clone https://github.com/nktkt/data-cleaning.git
cd data-cleaning
bash scripts/install.sh          # builds zig-out/bin/dataclean
PREFIX=$HOME/.local bash scripts/install.sh   # also installs to $PREFIX/bin/dataclean
```

The release binary is around 340 KB and has no runtime dependencies. Verified on macOS arm64.

## Usage

```
dataclean [OPTIONS] [INPUT]
```

`INPUT` is a file path. Omit or pass `-` to read stdin. Output goes to stdout unless `--output FILE` is given.

### Options

| Flag | Effect |
|------|--------|
| `--trim` | Trim leading/trailing whitespace from each cell. |
| `--collapse-ws` | Collapse internal runs of whitespace to a single space. |
| `--strip-bom` | Strip a leading UTF-8 BOM if present. |
| `--normalize-eol` | Convert CR / CRLF to LF. |
| `--strip-control` | Remove ASCII control bytes (preserves tab). |
| `--smart-quotes` | Convert curly quotes (U+2018/19/1C/1D) to straight ASCII. |
| `--lowercase` | Lowercase ASCII letters in cells. |
| `--drop-empty` | Drop rows whose cells are all empty / whitespace. |
| `--dedupe` | Drop duplicate rows (after other transforms). |
| `--normalize-nulls` | Replace recognized null tokens with the empty string. |
| `--null-tokens=A,B,C` | Override the default null-token set. |
| `--fill-na=zero\|mean\|drop` | Fill empty cells with 0, the column mean, or drop the row. |
| `--detect-types` | Profile each column's type to stderr. |
| `--outliers=iqr\|zscore` | Flag numeric outliers to stderr. |
| `--outlier-k=N` | k for IQR (default 1.5) or z-score threshold (default 3.0). |
| `--validate=COL:RULE` | Audit-only validation. Rules: `required`, `range=LO..HI`, `regex=PAT`, `enum=A,B,C`. Repeatable. |
| `--all` | Bundle: trim, collapse-ws, strip-bom, normalize-eol, strip-control, smart-quotes, drop-empty, dedupe, normalize-nulls. |
| `--delimiter=C` | Field delimiter (default `,`). |
| `--no-header` | Treat the first line as data, not a header. |
| `--output=FILE` | Write to FILE instead of stdout. |
| `--stats` | Print summary stats to stderr. |
| `--strict` | Exit code 1 if any validation rule fails. |
| `--version`, `--help` | Self-explanatory. |

## Examples

Quick clean of an Excel-exported CSV:

```bash
dataclean --strip-bom --normalize-eol --trim --collapse-ws input.csv --output cleaned.csv
```

Audit before doing anything:

```bash
dataclean --detect-types --outliers=iqr --stats input.csv
```

Validation gate for a data load (CI-friendly):

```bash
dataclean \
  --validate=email:required \
  --validate=email:regex=@ \
  --validate=age:range=0..120 \
  --strict \
  users.csv > /dev/null
```

Stream from stdin:

```bash
cat raw.csv | dataclean --all --detect-types | other-tool
```

TSV input:

```bash
dataclean --delimiter=$'\t' --all input.tsv --output cleaned.tsv
```

Fill missing numeric values with column mean and flag outliers afterwards:

```bash
dataclean --fill-na=mean --outliers=iqr --detect-types data.csv --output filled.csv
```

Atomic in-place rewrite:

```bash
dataclean --all data.csv --output data.csv.tmp && mv data.csv.tmp data.csv
```

More recipes are in [`references/recipes.md`](references/recipes.md).

## Tests

```bash
bash scripts/test.sh
```

Runs `zig build test` (11 unit tests) followed by 16 end-to-end shell assertions on the release binary. Total: 27 checks.

The test script verifies row counts, exit codes, and the contents of stderr reports. Use it both during development and as a smoke test after building on a new machine.

## Project layout

```
data-cleaning/
├── SKILL.md              Skill definition (Claude Code)
├── README.md             This file
├── build.zig             Build + test steps
├── src/main.zig          Implementation + unit tests
├── scripts/
│   ├── install.sh        Release build, optional system install
│   └── test.sh           Full test runner
├── fixtures/
│   ├── dirty.csv         Bundled-issue fixture
│   ├── dirty.csv.expected.txt
│   ├── dirty.json
│   └── simple.csv        Clean baseline
└── references/
    ├── operations.md     Algorithm / design notes per operation
    ├── recipes.md        Common CLI recipes
    └── zig_idioms.md     Zig 0.15.2 stdlib patterns used here
```

## As a Claude Code skill

This repository is also a self-contained [Claude Code skill](https://docs.claude.com/en/docs/claude-code). The `SKILL.md` frontmatter identifies it to Claude, and the `references/` directory holds documents Claude can pull from when invoked.

To use it as a skill, copy or symlink the directory under `~/.claude/skills/` (or place it in a Claude Code plugin), then build the binary once with `bash scripts/install.sh`. Claude can then run `dataclean` directly via the `Bash` tool.

## Limitations

- Single-byte delimiters only.
- Regex validation is substring/literal match, not a full regex engine.
- `--fill-na=mean` falls back to `0` for non-numeric columns.
- Validation rules report; they do not drop rows. Use `--strict` for a non-zero exit, or `--fill-na=drop` for empty-cell removal.
- Whole input is loaded into memory. Hard ceiling: 1 GiB per file.
- Smart-quote conversion handles the common four code points (U+2018/19/1C/1D); broader Unicode normalization is intentionally out of scope.

## License

MIT.
