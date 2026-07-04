# Data Cleaning Operations Reference

Reference for the Zig CLI data cleaner. Each operation lists: description, when to use, CLI flag, and a one-line algorithm note. Scope is constrained to what is implementable in a small Zig binary using only the standard library.

---

## 1. CSV Cleaning Operations

### 1.1 Trim whitespace
- **Description**: Strip leading/trailing ASCII whitespace from each field.
- **When**: Imports from spreadsheets or hand-edited CSVs.
- **Flag**: `--trim`
- **Algorithm**: For each field, advance start past `[ \t]`, retreat end past `[ \t]`.

### 1.2 Normalize line endings
- **Description**: Convert `CRLF` and lone `CR` to `LF`.
- **When**: Mixed-OS data sources.
- **Flag**: `--normalize-eol`
- **Algorithm**: Single-pass byte rewrite: `\r\n` -> `\n`, then standalone `\r` -> `\n`.

### 1.3 Deduplicate rows
- **Description**: Remove rows whose full field tuple has been seen.
- **When**: Concatenated exports, accidental double-imports.
- **Flag**: `--dedupe` (optional `--dedupe-keys=col1,col2`)
- **Algorithm**: Hash each row (FNV-1a over joined fields) into a `HashMap`; emit only on first sight.

### 1.4 Drop empty rows
- **Description**: Remove rows where every field is empty or whitespace only.
- **When**: Trailing blank lines, gaps between sections.
- **Flag**: `--drop-empty`
- **Algorithm**: Keep row iff any field has at least one non-whitespace byte.

### 1.5 Fix inconsistent quoting
- **Description**: Re-quote fields that contain delimiter, quote, or newline; unquote fields that do not need it.
- **When**: Hand-edited CSVs, mixed exporters.
- **Flag**: `--fix-quoting`
- **Algorithm**: Parse with RFC 4180 state machine; on emit, quote iff field contains `,`, `"`, `\n`, or `\r`; double internal `"`.

### 1.6 Handle BOM
- **Description**: Strip UTF-8 BOM (`EF BB BF`) from first line.
- **When**: Files exported from Excel or Windows tools.
- **Flag**: `--strip-bom` (default on)
- **Algorithm**: If first three bytes are BOM, advance read cursor by 3.

### 1.7 Detect / normalize delimiters
- **Description**: Auto-detect delimiter (`,`, `;`, `\t`, `|`) and optionally rewrite to a target delimiter.
- **When**: Unknown source format, or unifying a batch.
- **Flag**: `--detect-delim`, `--delim=,`, `--out-delim=,`
- **Algorithm**: Sniff first N=10 lines; pick the candidate with the most stable per-line count and highest median frequency.

### 1.8 Strip control characters
- **Description**: Remove ASCII control bytes (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F, 0x7F) from fields.
- **When**: Data from binary-tainted sources or copy-pasted output.
- **Flag**: `--strip-control`
- **Algorithm**: Per-byte filter; preserve `\t`, `\n`, `\r` until line-ending normalization runs.

---

## 2. Text Normalization

### 2.1 Unicode NFC / NFKC (described, not implemented)
- **Description**: NFC composes canonical-equivalent sequences; NFKC additionally folds compatibility variants (e.g. fullwidth digits, ligatures).
- **When**: Cross-source string matching, deduping records keyed on names.
- **Flag**: `--unicode=nfc|nfkc` (stub; emits a warning that full Unicode is not handled)
- **Algorithm**: Out of scope without a Unicode database; document the limitation and pass bytes through.

### 2.2 Lowercase ASCII
- **Description**: Map `A-Z` to `a-z`; non-ASCII bytes untouched.
- **When**: Case-insensitive joins/dedupe on ASCII-only columns.
- **Flag**: `--lower-ascii`
- **Algorithm**: `if (b >= 'A' and b <= 'Z') b += 32`.

### 2.3 Collapse whitespace runs
- **Description**: Replace runs of `[ \t]+` with a single space; optionally also collapse internal newlines in fields.
- **When**: Free-text columns with ragged spacing.
- **Flag**: `--collapse-ws`
- **Algorithm**: State flag `in_ws`; emit one space on first ws byte, skip subsequent ws.

### 2.4 Strip HTML-ish tags
- **Description**: Remove naive `<...>` spans and decode a fixed set of entities (`&amp; &lt; &gt; &quot; &#39; &nbsp;`).
- **When**: Scraped content where structure is not needed.
- **Flag**: `--strip-tags`
- **Algorithm**: Skip bytes between `<` and the next `>`; second pass replaces the listed entities. Not a real HTML parser; document it.

### 2.5 Smart quotes to ASCII
- **Description**: Replace common typographic punctuation with ASCII equivalents.
- **When**: Text copied from word processors or web pages.
- **Flag**: `--ascii-quotes`
- **Algorithm**: Byte-pattern substitution: U+2018/U+2019 -> `'`, U+201C/U+201D -> `"`, U+2013/U+2014 -> `-`, U+2026 -> `...`, U+00A0 -> ` `.

---

## 3. Null / Missing Value Handling

### 3.1 Recognized null tokens
- **Description**: Treat configured tokens as missing. Default set: `""`, `NA`, `N/A`, `null`, `NULL`, `-`, `?`.
- **When**: Sources that encode missing values inconsistently.
- **Flag**: `--null-tokens=NA,N/A,null,NULL,-,?` (case-sensitive unless `--null-ci`)
- **Algorithm**: After trim, compare field against token set; on match, mark cell as null.

### 3.2 Drop rows with nulls
- **Description**: Remove a row if any (or any specified) column is null.
- **When**: Strict downstream consumer.
- **Flag**: `--drop-na` or `--drop-na=col1,col2`
- **Algorithm**: Per row: skip if any selected column is null.

### 3.3 Fill with default
- **Description**: Replace null with a fixed literal per column.
- **When**: Known sentinel substitution, e.g. `country=Unknown`.
- **Flag**: `--fill-na=col=value` (repeatable)
- **Algorithm**: Direct substitution at emit time.

### 3.4 Fill numeric with column statistic
- **Description**: Replace null with the column mean (also supports `median`, `min`, `max`, `zero`).
- **When**: Numeric columns where dropping rows is too costly.
- **Flag**: `--fill-na=mean` (or `median|min|max|zero`)
- **Algorithm**: Two-pass: pass 1 computes statistic over non-null parsed numerics; pass 2 substitutes.

---

## 4. Type Coercion

### 4.1 Detect column types
- **Description**: Infer one of `int`, `float`, `bool`, `date`, `string` per column.
- **When**: Auto-formatting, schema reporting, downstream type hints.
- **Flag**: `--detect-types`
- **Algorithm**: For each non-null cell, try parsers in order `bool -> int -> float -> date -> string`; column type = most-specific type accepted by all cells.

### 4.2 Parser rules
- **bool**: `true|false|yes|no|y|n|0|1` (case-insensitive).
- **int**: optional sign, then `[0-9]+`, fits `i64`.
- **float**: `std.fmt.parseFloat` accepts; reject if also pure int and that is preferred.
- **date**: `YYYY-MM-DD`, `YYYY/MM/DD`, `DD-MM-YYYY` (configurable).
- **string**: fallback.

### 4.3 Report mixed-type columns
- **Description**: Emit a diagnostic for columns where no single non-string type covers all cells.
- **When**: Data quality audits.
- **Flag**: `--report-mixed`
- **Algorithm**: Track count per attempted type per column; flag columns where the dominant type covers < 100% but > some threshold (default 80%).

### 4.4 Coerce to declared type
- **Description**: Force-parse a column; rows that fail are flagged or dropped.
- **When**: Strict schema mode.
- **Flag**: `--coerce=col:int` (repeatable), `--on-coerce-fail=drop|null|keep`
- **Algorithm**: Apply the matching parser; route failures per policy.

---

## 5. Outlier Detection (Numeric Columns)

### 5.1 IQR method
- **Description**: Flag values outside `[Q1 - k*IQR, Q3 + k*IQR]`, where `IQR = Q3 - Q1`, default `k = 1.5`.
- **When**: Skewed or non-normal distributions; robust to extremes.
- **Flag**: `--outlier=iqr:col[:k]`
- **Algorithm**: Sort column, take 25th and 75th percentiles by linear interpolation, compute bounds, scan and flag.

### 5.2 Z-score method
- **Description**: Flag values where `|z| > t`, with `z = (x - mean) / stddev`, default `t = 3.0`.
- **When**: Roughly normal distributions, large samples.
- **Flag**: `--outlier=zscore:col[:t]`
- **Algorithm**: Compute mean and (population) stddev in one pass via Welford; second pass flags by threshold.

### 5.3 Outlier action
- **Description**: What to do on detection.
- **Flag**: `--outlier-action=flag|drop|null|clip`
- **Algorithm**: `flag` adds an `_outlier` boolean column; `clip` snaps to the bound; `null` blanks the cell; `drop` removes the row.

---

## 6. Validation Rules

Rules are loaded from a small config (key=value lines or JSON) and checked per row. Default action on failure: report; configurable to drop.

### 6.1 Required columns
- **Description**: Fail if a named column is absent from the header.
- **When**: Schema enforcement on ingest.
- **Flag**: `--require-cols=id,name,email`
- **Algorithm**: Compare header set to required set; abort early on miss.

### 6.2 Regex match
- **Description**: Cell must match a pattern (use a small built-in subset: anchors, character classes, `*`, `+`, `?`, `|`, groups).
- **When**: ID/email/phone shape checks.
- **Flag**: `--match=col:^[A-Z]{2}[0-9]{6}$`
- **Algorithm**: Compile pattern once into an NFA; evaluate per cell.

### 6.3 Numeric range
- **Description**: Cell parsed as number must fall within `[min, max]` (either bound optional).
- **When**: Sanity bounds (age 0-120, percentage 0-100).
- **Flag**: `--range=col:0..120`
- **Algorithm**: Parse; compare; non-numeric is a failure.

### 6.4 Enum membership
- **Description**: Cell must be one of a fixed set.
- **When**: Status / category columns.
- **Flag**: `--enum=col:active,inactive,pending`
- **Algorithm**: Build a small `HashMap` of allowed values; lookup per cell. Honor `--enum-ci` for case-insensitive.

### 6.5 Validation reporting
- **Description**: Aggregate failures into a report.
- **Flag**: `--report=path.json` (or `--report=-` for stdout), `--on-fail=warn|drop|abort`
- **Algorithm**: Stream JSON lines `{row, col, rule, value, message}`; track counts for summary at end.

---

## Operation Order (Default Pipeline)

1. Strip BOM
2. Normalize line endings
3. Detect / set delimiter
4. Parse rows (RFC 4180)
5. Strip control chars
6. Trim whitespace
7. Collapse whitespace / strip tags / ASCII quotes / lowercase (text ops)
8. Fix quoting (re-emit policy)
9. Null token recognition
10. Type detection
11. Coercion
12. Fill / drop nulls
13. Outlier detection
14. Validation rules
15. Dedupe
16. Drop empty rows
17. Emit
