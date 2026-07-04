# `dataclean` Recipes

Common task recipes for the `dataclean` CLI. Each recipe shows the scenario, the exact command, and a brief note explaining the flag combination.

## 1. Quick clean

An Excel-exported CSV arrives with a UTF-8 BOM, mixed CRLF/LF line endings, and stray trailing whitespace in cells.

```bash
dataclean --strip-bom --normalize-eol --trim --collapse-ws input.csv --output cleaned.csv
```

Strips the leading BOM, normalizes line endings, and trims plus collapses whitespace inside fields so downstream parsers see consistent rows.

## 2. Strict dedup pipeline

A bulk-imported CSV has duplicate rows from repeated exports and blank lines from manual edits.

```bash
dataclean --all input.csv --output deduped.csv
```

`--all` is the safe one-shot bundle: it enables trim, collapse-ws, strip-bom, normalize-eol, strip-control, smart-quotes, drop-empty, dedupe, and normalize-nulls without touching numeric semantics.

## 3. Audit before cleaning

You want a read-only inspection of an unfamiliar dataset before deciding on a cleaning strategy.

```bash
dataclean --detect-types --outliers=iqr --stats input.csv
```

No mutating flags and no `--output`, so the file is untouched; type detection, IQR outlier flagging, and `--stats` together produce a profile report only.

## 4. Numeric column with outliers and missing values

A measurements CSV has gaps in a numeric column and a few extreme values you want surfaced.

```bash
dataclean --detect-types --fill-na=mean --outliers=iqr --outlier-k=1.5 input.csv --output filled.csv
```

Type detection enables numeric handling, `--fill-na=mean` imputes missing cells, and IQR with `k=1.5` (the standard fence) flags outliers after imputation so the mean is not skewed by gaps.

## 5. Validation gate for a data load

Before importing user records, enforce that email is present and looks valid, and that age is in a sane range.

```bash
dataclean --validate=email:required --validate=email:regex='.+@.+' --validate=age:range=0..120 users.csv --output users_valid.csv
```

Stacked `--validate` rules act as an audit gate: `required` checks emails are non-empty, `regex` enforces an `@`, `range=0..120` bounds age. Failing rows are still emitted to the output; use the stderr report (and a non-zero failure count) to decide whether to proceed with the load.

## 6. Stream from stdin in a pipeline

You are composing `dataclean` between two other Unix tools without writing a temp file.

```bash
cat raw.csv | dataclean --all --detect-types | other-tool
```

Omitting the input path makes `dataclean` read stdin and write stdout, so it slots cleanly into a shell pipeline; `--all` plus `--detect-types` gives a sensible default cleanup.

## 7. Custom null tokens for legacy data

A legacy export uses sentinels like `N/A`, `--`, and `unknown` instead of empty cells.

```bash
dataclean --null-tokens=N/A,--,unknown --normalize-nulls --fill-na=drop legacy.csv --output legacy_clean.csv
```

`--null-tokens` teaches the parser which strings count as missing, `--normalize-nulls` rewrites them to a canonical empty form, and `--fill-na=drop` removes rows that still have nulls afterwards.

## 8. TSV instead of CSV

The input is tab-separated rather than comma-separated.

```bash
dataclean --delimiter=$'\t' --all input.tsv --output cleaned.tsv
```

`--delimiter` overrides the default comma so fields parse correctly; everything else (including `--all`) works the same on TSV input.

## 9. Headerless CSV

A machine-generated CSV has no header row and columns are referenced positionally downstream.

```bash
dataclean --no-header --all --detect-types data.csv --output data_clean.csv
```

`--no-header` tells `dataclean` to treat the first line as data, not column names, so `--detect-types` profiles every row and no row is silently consumed as a header.

## 10. Write cleaned file in place via temp

You want to overwrite the original file but keep the operation atomic if the run fails.

```bash
dataclean --all data.csv --output data.csv.tmp && mv data.csv.tmp data.csv
```

Writing to a sibling temp path with `--output` and renaming on success avoids truncating `data.csv` mid-run; if `dataclean` exits non-zero, the original remains intact.
