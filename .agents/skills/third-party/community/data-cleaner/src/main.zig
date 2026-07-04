const std = @import("std");

const VERSION = "1.1.0";

const Options = struct {
    trim: bool = false,
    collapse_ws: bool = false,
    strip_bom: bool = false,
    normalize_eol: bool = false,
    strip_control: bool = false,
    smart_quotes: bool = false,
    lowercase: bool = false,
    drop_empty: bool = false,
    dedupe: bool = false,
    normalize_nulls: bool = false,
    null_tokens: []const []const u8 = &default_null_tokens,
    fill_na: ?FillStrategy = null,
    detect_types: bool = false,
    outlier_method: ?OutlierMethod = null,
    outlier_k: f64 = 1.5,
    delimiter: u8 = ',',
    no_header: bool = false,
    stats: bool = false,
    output_path: ?[]const u8 = null,
    input_path: ?[]const u8 = null,
    validations: []Validation = &.{},
    strict: bool = false,
};

const FillStrategy = enum { zero, mean, drop };
const OutlierMethod = enum { iqr, zscore };

const Validation = struct {
    column: []const u8,
    rule: Rule,
};

const Rule = union(enum) {
    required: void,
    regex_prefix: []const u8, // simplified: prefix match
    range: struct { lo: f64, hi: f64 },
    enum_set: [][]const u8,
};

const default_null_tokens = [_][]const u8{ "", "NA", "N/A", "null", "NULL", "-", "?", "n/a", "Null" };

const ColType = enum { empty, integer, float, boolean, string };

const Row = struct {
    fields: [][]u8,
};

const Table = struct {
    header: ?[][]u8,
    rows: std.ArrayList(Row),
    arena: std.heap.ArenaAllocator,

    fn deinit(self: *Table) void {
        self.arena.deinit();
    }

    fn columnCount(self: *const Table) usize {
        if (self.header) |h| return h.len;
        if (self.rows.items.len > 0) return self.rows.items[0].fields.len;
        return 0;
    }

    fn columnIndex(self: *const Table, name: []const u8) ?usize {
        const h = self.header orelse return null;
        for (h, 0..) |col, i| if (std.mem.eql(u8, col, name)) return i;
        return null;
    }
};

// =============================================================================
// CLI parsing
// =============================================================================

fn printHelp(w: *std.Io.Writer) !void {
    const help =
        \\dataclean — fast, simple CSV/text cleaner (v
    ++ VERSION ++
        \\)
        \\
        \\USAGE:
        \\  dataclean [OPTIONS] [INPUT]
        \\
        \\INPUT:
        \\  Path to a CSV file. If omitted or '-', read from stdin.
        \\
        \\OUTPUT:
        \\  Cleaned CSV written to stdout (or --output PATH).
        \\
        \\PIPELINE OPTIONS:
        \\  --trim               Trim leading/trailing whitespace from each cell
        \\  --collapse-ws        Collapse internal whitespace runs to single space
        \\  --strip-bom          Strip UTF-8 BOM from start of input
        \\  --normalize-eol      Convert CR/CRLF line endings to LF
        \\  --strip-control      Strip ASCII control chars (preserves tab/space)
        \\  --smart-quotes       Convert curly/smart quotes to straight ASCII quotes
        \\  --lowercase          Lowercase ASCII letters in cells
        \\  --drop-empty         Drop rows where every cell is empty/whitespace
        \\  --dedupe             Drop duplicate rows (after other ops)
        \\  --normalize-nulls    Replace recognized null tokens with empty string
        \\  --null-tokens=A,B,C  Override default null tokens (use with --normalize-nulls)
        \\  --fill-na=STRATEGY   For empty cells: zero | mean | drop
        \\  --detect-types       Print column type-detection report to stderr
        \\  --outliers=METHOD    iqr | zscore — report outliers to stderr
        \\  --outlier-k=N        k for IQR (default 1.5) or threshold for zscore (default 3)
        \\  --validate=COL:RULE  Validate. RULE: required, range=LO..HI, regex=PAT, enum=A,B,C
        \\  --all                Enable trim, collapse-ws, strip-bom, normalize-eol,
        \\                       strip-control, smart-quotes, drop-empty, dedupe,
        \\                       normalize-nulls
        \\
        \\FORMAT OPTIONS:
        \\  --delimiter=C        Field delimiter (default: ,)
        \\  --no-header          Treat first line as data, not header
        \\  --output=FILE        Write to FILE instead of stdout
        \\  --stats              Print summary stats to stderr
        \\  --strict             Exit code 1 if any validation rule fails
        \\
        \\OTHER:
        \\  --version            Print version
        \\  --help               Print this help
        \\
        \\EXAMPLES:
        \\  dataclean --all dirty.csv
        \\  cat dirty.csv | dataclean --trim --dedupe --drop-empty
        \\  dataclean --normalize-nulls --fill-na=mean data.csv > clean.csv
        \\  dataclean --validate=email:regex=@ --validate=age:range=0..120 in.csv
        \\
    ;
    try w.writeAll(help);
}

fn parseArgs(allocator: std.mem.Allocator, args: [][:0]u8) !Options {
    var opts = Options{};
    var validations = std.ArrayList(Validation){};
    errdefer validations.deinit(allocator);

    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const a = args[i];
        if (std.mem.eql(u8, a, "--help") or std.mem.eql(u8, a, "-h")) {
            opts.input_path = "__HELP__";
            return opts;
        } else if (std.mem.eql(u8, a, "--version")) {
            opts.input_path = "__VERSION__";
            return opts;
        } else if (std.mem.eql(u8, a, "--trim")) {
            opts.trim = true;
        } else if (std.mem.eql(u8, a, "--collapse-ws")) {
            opts.collapse_ws = true;
        } else if (std.mem.eql(u8, a, "--strip-bom")) {
            opts.strip_bom = true;
        } else if (std.mem.eql(u8, a, "--normalize-eol")) {
            opts.normalize_eol = true;
        } else if (std.mem.eql(u8, a, "--strip-control")) {
            opts.strip_control = true;
        } else if (std.mem.eql(u8, a, "--smart-quotes")) {
            opts.smart_quotes = true;
        } else if (std.mem.eql(u8, a, "--lowercase")) {
            opts.lowercase = true;
        } else if (std.mem.eql(u8, a, "--drop-empty")) {
            opts.drop_empty = true;
        } else if (std.mem.eql(u8, a, "--dedupe")) {
            opts.dedupe = true;
        } else if (std.mem.eql(u8, a, "--normalize-nulls")) {
            opts.normalize_nulls = true;
        } else if (std.mem.eql(u8, a, "--detect-types")) {
            opts.detect_types = true;
        } else if (std.mem.eql(u8, a, "--no-header")) {
            opts.no_header = true;
        } else if (std.mem.eql(u8, a, "--stats")) {
            opts.stats = true;
        } else if (std.mem.eql(u8, a, "--strict")) {
            opts.strict = true;
        } else if (std.mem.eql(u8, a, "--all")) {
            opts.trim = true;
            opts.collapse_ws = true;
            opts.strip_bom = true;
            opts.normalize_eol = true;
            opts.strip_control = true;
            opts.smart_quotes = true;
            opts.drop_empty = true;
            opts.dedupe = true;
            opts.normalize_nulls = true;
        } else if (std.mem.startsWith(u8, a, "--null-tokens=")) {
            const val = a["--null-tokens=".len..];
            var list = std.ArrayList([]const u8){};
            var it = std.mem.tokenizeScalar(u8, val, ',');
            while (it.next()) |tok| try list.append(allocator, tok);
            opts.null_tokens = try list.toOwnedSlice(allocator);
        } else if (std.mem.startsWith(u8, a, "--fill-na=")) {
            const val = a["--fill-na=".len..];
            opts.fill_na = std.meta.stringToEnum(FillStrategy, val) orelse {
                std.debug.print("error: unknown fill-na strategy '{s}'\n", .{val});
                return error.BadArgs;
            };
        } else if (std.mem.startsWith(u8, a, "--outliers=")) {
            const val = a["--outliers=".len..];
            opts.outlier_method = std.meta.stringToEnum(OutlierMethod, val) orelse {
                std.debug.print("error: unknown outliers method '{s}'\n", .{val});
                return error.BadArgs;
            };
            if (opts.outlier_method == .zscore) opts.outlier_k = 3.0;
        } else if (std.mem.startsWith(u8, a, "--outlier-k=")) {
            const val = a["--outlier-k=".len..];
            opts.outlier_k = try std.fmt.parseFloat(f64, val);
        } else if (std.mem.startsWith(u8, a, "--delimiter=")) {
            const val = a["--delimiter=".len..];
            if (val.len != 1) {
                std.debug.print("error: delimiter must be one byte\n", .{});
                return error.BadArgs;
            }
            opts.delimiter = val[0];
        } else if (std.mem.startsWith(u8, a, "--output=")) {
            opts.output_path = a["--output=".len..];
        } else if (std.mem.startsWith(u8, a, "--validate=")) {
            const val = a["--validate=".len..];
            const v = try parseValidation(allocator, val);
            try validations.append(allocator, v);
        } else if (std.mem.startsWith(u8, a, "--")) {
            std.debug.print("error: unknown option '{s}'\n", .{a});
            return error.BadArgs;
        } else {
            // positional input
            opts.input_path = a;
        }
    }

    opts.validations = try validations.toOwnedSlice(allocator);
    return opts;
}

fn parseValidation(allocator: std.mem.Allocator, spec: []const u8) !Validation {
    const colon = std.mem.indexOfScalar(u8, spec, ':') orelse return error.BadArgs;
    const col = spec[0..colon];
    const rest = spec[colon + 1 ..];
    if (std.mem.eql(u8, rest, "required")) {
        return .{ .column = col, .rule = .required };
    } else if (std.mem.startsWith(u8, rest, "regex=")) {
        return .{ .column = col, .rule = .{ .regex_prefix = rest["regex=".len..] } };
    } else if (std.mem.startsWith(u8, rest, "range=")) {
        const r = rest["range=".len..];
        const sep = std.mem.indexOf(u8, r, "..") orelse return error.BadArgs;
        const lo = try std.fmt.parseFloat(f64, r[0..sep]);
        const hi = try std.fmt.parseFloat(f64, r[sep + 2 ..]);
        return .{ .column = col, .rule = .{ .range = .{ .lo = lo, .hi = hi } } };
    } else if (std.mem.startsWith(u8, rest, "enum=")) {
        const e = rest["enum=".len..];
        var list = std.ArrayList([]const u8){};
        var it = std.mem.tokenizeScalar(u8, e, ',');
        while (it.next()) |tok| try list.append(allocator, tok);
        return .{ .column = col, .rule = .{ .enum_set = try list.toOwnedSlice(allocator) } };
    }
    return error.BadArgs;
}

// =============================================================================
// I/O
// =============================================================================

fn readAll(allocator: std.mem.Allocator, path: ?[]const u8) ![]u8 {
    const max = 1024 * 1024 * 1024; // 1 GiB ceiling
    if (path) |p| {
        if (std.mem.eql(u8, p, "-")) {
            return try std.fs.File.stdin().readToEndAlloc(allocator, max);
        }
        const f = try std.fs.cwd().openFile(p, .{});
        defer f.close();
        return try f.readToEndAlloc(allocator, max);
    }
    return try std.fs.File.stdin().readToEndAlloc(allocator, max);
}

// =============================================================================
// Preprocessing (operates on the raw byte buffer)
// =============================================================================

fn stripBom(input: []const u8) []const u8 {
    if (input.len >= 3 and input[0] == 0xEF and input[1] == 0xBB and input[2] == 0xBF) {
        return input[3..];
    }
    return input;
}

fn normalizeEol(allocator: std.mem.Allocator, input: []const u8) ![]u8 {
    var out = try std.ArrayList(u8).initCapacity(allocator, input.len);
    var i: usize = 0;
    while (i < input.len) : (i += 1) {
        const c = input[i];
        if (c == '\r') {
            try out.append(allocator, '\n');
            if (i + 1 < input.len and input[i + 1] == '\n') i += 1;
        } else {
            try out.append(allocator, c);
        }
    }
    return out.toOwnedSlice(allocator);
}

// =============================================================================
// CSV parsing — RFC4180-ish
// =============================================================================

fn parseCsv(arena: std.mem.Allocator, input: []const u8, delimiter: u8) !struct {
    rows: std.ArrayList(Row),
} {
    var rows = std.ArrayList(Row){};
    var current_row = std.ArrayList([]u8){};
    var current_field = std.ArrayList(u8){};

    var in_quotes = false;
    var i: usize = 0;
    while (i < input.len) : (i += 1) {
        const c = input[i];
        if (in_quotes) {
            if (c == '"') {
                if (i + 1 < input.len and input[i + 1] == '"') {
                    try current_field.append(arena, '"');
                    i += 1;
                } else {
                    in_quotes = false;
                }
            } else {
                try current_field.append(arena, c);
            }
        } else {
            if (c == '"' and current_field.items.len == 0) {
                in_quotes = true;
            } else if (c == delimiter) {
                try current_row.append(arena, try current_field.toOwnedSlice(arena));
                current_field = std.ArrayList(u8){};
            } else if (c == '\n') {
                try current_row.append(arena, try current_field.toOwnedSlice(arena));
                current_field = std.ArrayList(u8){};
                try rows.append(arena, .{ .fields = try current_row.toOwnedSlice(arena) });
                current_row = std.ArrayList([]u8){};
            } else if (c == '\r') {
                // skipped — should be handled by normalize-eol, but be tolerant
                continue;
            } else {
                try current_field.append(arena, c);
            }
        }
    }

    // flush last field/row if any content remains
    if (current_field.items.len > 0 or current_row.items.len > 0) {
        try current_row.append(arena, try current_field.toOwnedSlice(arena));
        try rows.append(arena, .{ .fields = try current_row.toOwnedSlice(arena) });
    }

    return .{ .rows = rows };
}

// =============================================================================
// Cell-level transformations
// =============================================================================

fn transformCell(arena: std.mem.Allocator, cell: []const u8, opts: *const Options) ![]u8 {
    var buf = std.ArrayList(u8){};
    try buf.ensureTotalCapacity(arena, cell.len);

    // Pass 1: byte-level transforms (smart quotes, control strip)
    var i: usize = 0;
    while (i < cell.len) {
        // Smart quotes: U+2018 U+2019 U+201C U+201D — UTF-8: E2 80 98/99/9C/9D
        if (opts.smart_quotes and i + 2 < cell.len and cell[i] == 0xE2 and cell[i + 1] == 0x80) {
            const b = cell[i + 2];
            if (b == 0x98 or b == 0x99) {
                try buf.append(arena, '\'');
                i += 3;
                continue;
            } else if (b == 0x9C or b == 0x9D) {
                try buf.append(arena, '"');
                i += 3;
                continue;
            }
        }
        const c = cell[i];
        if (opts.strip_control and c < 0x20 and c != '\t') {
            i += 1;
            continue;
        }
        if (opts.lowercase and c >= 'A' and c <= 'Z') {
            try buf.append(arena, c + 32);
            i += 1;
            continue;
        }
        try buf.append(arena, c);
        i += 1;
    }

    var s: []u8 = buf.items;

    if (opts.trim) s = trimSlice(s);

    if (opts.collapse_ws) {
        var out = std.ArrayList(u8){};
        try out.ensureTotalCapacity(arena, s.len);
        var prev_ws = false;
        for (s) |c| {
            const ws = c == ' ' or c == '\t';
            if (ws) {
                if (!prev_ws) try out.append(arena, ' ');
                prev_ws = true;
            } else {
                try out.append(arena, c);
                prev_ws = false;
            }
        }
        s = out.items;
    }

    if (opts.normalize_nulls) {
        for (opts.null_tokens) |tok| {
            if (std.mem.eql(u8, s, tok)) {
                s = "";
                break;
            }
        }
    }

    // Need a stable copy because we sliced into intermediate buffers
    return try arena.dupe(u8, s);
}

fn trimSlice(s: []u8) []u8 {
    var lo: usize = 0;
    var hi: usize = s.len;
    while (lo < hi and isSpace(s[lo])) lo += 1;
    while (hi > lo and isSpace(s[hi - 1])) hi -= 1;
    return s[lo..hi];
}

fn isSpace(c: u8) bool {
    return c == ' ' or c == '\t' or c == '\r' or c == '\n';
}

// =============================================================================
// Row-level operations
// =============================================================================

fn rowIsEmpty(row: *const Row) bool {
    for (row.fields) |f| {
        for (f) |c| {
            if (!isSpace(c)) return false;
        }
    }
    return true;
}

fn rowHash(row: *const Row, delimiter: u8) u64 {
    var h = std.hash.Fnv1a_64.init();
    for (row.fields, 0..) |f, idx| {
        if (idx > 0) {
            const d = [_]u8{delimiter};
            h.update(&d);
        }
        h.update(f);
    }
    return h.final();
}

// =============================================================================
// Type detection
// =============================================================================

fn detectCellType(s: []const u8) ColType {
    if (s.len == 0) return .empty;
    if (std.mem.eql(u8, s, "true") or std.mem.eql(u8, s, "false") or
        std.mem.eql(u8, s, "TRUE") or std.mem.eql(u8, s, "FALSE")) return .boolean;
    _ = std.fmt.parseInt(i64, s, 10) catch {
        _ = std.fmt.parseFloat(f64, s) catch return .string;
        return .float;
    };
    return .integer;
}

fn mergeTypes(a: ColType, b: ColType) ColType {
    if (a == .empty) return b;
    if (b == .empty) return a;
    if (a == b) return a;
    // integer + float -> float
    if ((a == .integer and b == .float) or (a == .float and b == .integer)) return .float;
    return .string;
}

fn typeName(t: ColType) []const u8 {
    return switch (t) {
        .empty => "empty",
        .integer => "integer",
        .float => "float",
        .boolean => "boolean",
        .string => "string",
    };
}

// =============================================================================
// CSV writing
// =============================================================================

fn writeCell(w: *std.Io.Writer, cell: []const u8, delimiter: u8) !void {
    var needs_quote = false;
    for (cell) |c| {
        if (c == delimiter or c == '"' or c == '\n' or c == '\r') {
            needs_quote = true;
            break;
        }
    }
    if (!needs_quote) {
        try w.writeAll(cell);
        return;
    }
    try w.writeByte('"');
    for (cell) |c| {
        if (c == '"') try w.writeByte('"');
        try w.writeByte(c);
    }
    try w.writeByte('"');
}

fn writeRow(w: *std.Io.Writer, row: *const Row, delimiter: u8) !void {
    for (row.fields, 0..) |f, i| {
        if (i > 0) try w.writeByte(delimiter);
        try writeCell(w, f, delimiter);
    }
    try w.writeByte('\n');
}

// =============================================================================
// Validation, fill-na, outliers
// =============================================================================

fn columnNumericValues(arena: std.mem.Allocator, table: *const Table, col: usize) !std.ArrayList(f64) {
    var values = std.ArrayList(f64){};
    for (table.rows.items) |r| {
        if (col >= r.fields.len) continue;
        const v = std.fmt.parseFloat(f64, r.fields[col]) catch continue;
        try values.append(arena, v);
    }
    return values;
}

fn computeMean(values: []const f64) f64 {
    if (values.len == 0) return 0;
    var sum: f64 = 0;
    for (values) |v| sum += v;
    return sum / @as(f64, @floatFromInt(values.len));
}

fn computeStdDev(values: []const f64, mean: f64) f64 {
    if (values.len < 2) return 0;
    var ss: f64 = 0;
    for (values) |v| {
        const d = v - mean;
        ss += d * d;
    }
    return @sqrt(ss / @as(f64, @floatFromInt(values.len - 1)));
}

fn percentile(sorted: []const f64, p: f64) f64 {
    if (sorted.len == 0) return 0;
    if (sorted.len == 1) return sorted[0];
    const idx = p * @as(f64, @floatFromInt(sorted.len - 1));
    const lo: usize = @intFromFloat(@floor(idx));
    const hi: usize = @intFromFloat(@ceil(idx));
    if (lo == hi) return sorted[lo];
    const frac = idx - @floor(idx);
    return sorted[lo] * (1 - frac) + sorted[hi] * frac;
}

fn applyFillNa(arena: std.mem.Allocator, table: *Table, strategy: FillStrategy) !void {
    if (strategy == .drop) {
        var kept = std.ArrayList(Row){};
        outer: for (table.rows.items) |r| {
            for (r.fields) |f| {
                if (f.len == 0) continue :outer;
            }
            try kept.append(arena, r);
        }
        table.rows.deinit(arena);
        table.rows = kept;
        return;
    }

    const cols = table.columnCount();
    var col_means = try arena.alloc(f64, cols);
    defer arena.free(col_means);

    for (0..cols) |c| {
        if (strategy == .zero) {
            col_means[c] = 0;
            continue;
        }
        const vals = try columnNumericValues(arena, table, c);
        col_means[c] = computeMean(vals.items);
    }

    for (table.rows.items) |r| {
        for (r.fields, 0..) |*f, c| {
            if (f.*.len == 0 and c < cols) {
                if (strategy == .zero) {
                    f.* = try arena.dupe(u8, "0");
                } else {
                    f.* = try std.fmt.allocPrint(arena, "{d}", .{col_means[c]});
                }
            }
        }
    }
}

fn reportOutliers(arena: std.mem.Allocator, table: *const Table, opts: *const Options, errw: *std.Io.Writer) !void {
    const method = opts.outlier_method orelse return;
    const cols = table.columnCount();
    const headers = table.header;

    try errw.print("# outlier report (method={s}, k={d})\n", .{ @tagName(method), opts.outlier_k });
    for (0..cols) |c| {
        const raw = try columnNumericValues(arena, table, c);
        if (raw.items.len < 4) continue;
        const colname = if (headers) |h| h[c] else "";

        const sorted = try arena.dupe(f64, raw.items);
        std.mem.sort(f64, sorted, {}, std.sort.asc(f64));

        switch (method) {
            .iqr => {
                const q1 = percentile(sorted, 0.25);
                const q3 = percentile(sorted, 0.75);
                const iqr = q3 - q1;
                const lo = q1 - opts.outlier_k * iqr;
                const hi = q3 + opts.outlier_k * iqr;
                var count: usize = 0;
                for (sorted) |v| {
                    if (v < lo or v > hi) count += 1;
                }
                if (count > 0) {
                    if (headers != null) {
                        try errw.print("  col[{d}={s}] IQR Q1={d:.3} Q3={d:.3} bounds=[{d:.3},{d:.3}] outliers={d}\n", .{ c, colname, q1, q3, lo, hi, count });
                    } else {
                        try errw.print("  col[{d}] IQR Q1={d:.3} Q3={d:.3} bounds=[{d:.3},{d:.3}] outliers={d}\n", .{ c, q1, q3, lo, hi, count });
                    }
                }
            },
            .zscore => {
                const mean = computeMean(sorted);
                const sd = computeStdDev(sorted, mean);
                if (sd == 0) continue;
                var count: usize = 0;
                for (sorted) |v| {
                    const z = @abs((v - mean) / sd);
                    if (z > opts.outlier_k) count += 1;
                }
                if (count > 0) {
                    if (headers != null) {
                        try errw.print("  col[{d}={s}] zscore mean={d:.3} sd={d:.3} threshold={d} outliers={d}\n", .{ c, colname, mean, sd, opts.outlier_k, count });
                    } else {
                        try errw.print("  col[{d}] zscore mean={d:.3} sd={d:.3} threshold={d} outliers={d}\n", .{ c, mean, sd, opts.outlier_k, count });
                    }
                }
            },
        }
    }
}

fn reportTypes(arena: std.mem.Allocator, table: *const Table, errw: *std.Io.Writer) !void {
    const cols = table.columnCount();
    var types = try arena.alloc(ColType, cols);
    defer arena.free(types);
    for (types) |*t| t.* = .empty;

    for (table.rows.items) |r| {
        for (r.fields, 0..) |f, c| {
            if (c >= cols) continue;
            types[c] = mergeTypes(types[c], detectCellType(f));
        }
    }

    try errw.print("# column types\n", .{});
    for (types, 0..) |t, c| {
        const name = if (table.header) |h| h[c] else "";
        try errw.print("  col[{d}={s}] {s}\n", .{ c, name, typeName(t) });
    }
}

fn runValidations(table: *const Table, opts: *const Options, errw: *std.Io.Writer) !usize {
    var fail_count: usize = 0;
    for (opts.validations) |v| {
        const idx = table.columnIndex(v.column) orelse {
            try errw.print("  validation: column '{s}' not found\n", .{v.column});
            fail_count += 1;
            continue;
        };
        for (table.rows.items, 0..) |r, ri| {
            if (idx >= r.fields.len) continue;
            const cell = r.fields[idx];
            const ok = switch (v.rule) {
                .required => cell.len > 0,
                .regex_prefix => |pat| std.mem.indexOf(u8, cell, pat) != null,
                .range => |rg| blk: {
                    const x = std.fmt.parseFloat(f64, cell) catch break :blk false;
                    break :blk x >= rg.lo and x <= rg.hi;
                },
                .enum_set => |set| blk: {
                    for (set) |opt| if (std.mem.eql(u8, cell, opt)) break :blk true;
                    break :blk false;
                },
            };
            if (!ok) {
                try errw.print("  validation FAIL row={d} col={s} value='{s}'\n", .{ ri + 1, v.column, cell });
                fail_count += 1;
            }
        }
    }
    return fail_count;
}

// =============================================================================
// Pipeline
// =============================================================================

fn runPipeline(
    gpa: std.mem.Allocator,
    arena: std.mem.Allocator,
    raw_input: []const u8,
    opts: *const Options,
    out: *std.Io.Writer,
    errw: *std.Io.Writer,
) !usize {
    var working: []const u8 = raw_input;

    var validation_failures: usize = 0;

    if (opts.strip_bom) working = stripBom(working);
    if (opts.normalize_eol) {
        working = try normalizeEol(arena, working);
    }

    const parsed = try parseCsv(arena, working, opts.delimiter);
    var table = Table{
        .header = null,
        .rows = parsed.rows,
        .arena = std.heap.ArenaAllocator.init(gpa),
    };
    // The arena field above is only used for cleanup symmetry; we actually
    // already pass the caller's arena to all allocators. Deinit it now to
    // avoid leak warnings.
    table.arena.deinit();

    if (table.rows.items.len == 0) return 0;

    // Apply cell-level transforms across all rows
    for (table.rows.items) |*r| {
        for (r.fields) |*f| {
            f.* = try transformCell(arena, f.*, opts);
        }
    }

    // Split header from data
    if (!opts.no_header) {
        table.header = table.rows.items[0].fields;
        const data = table.rows.items[1..];
        var new_list = std.ArrayList(Row){};
        try new_list.ensureTotalCapacity(arena, data.len);
        for (data) |r| try new_list.append(arena, r);
        table.rows = new_list;
    }

    // Drop empty rows
    if (opts.drop_empty) {
        var kept = std.ArrayList(Row){};
        for (table.rows.items) |r| {
            if (!rowIsEmpty(&r)) try kept.append(arena, r);
        }
        table.rows = kept;
    }

    // Dedupe (after other transforms)
    if (opts.dedupe) {
        var seen = std.AutoHashMap(u64, void).init(arena);
        defer seen.deinit();
        var kept = std.ArrayList(Row){};
        for (table.rows.items) |r| {
            const h = rowHash(&r, opts.delimiter);
            if (seen.contains(h)) continue;
            try seen.put(h, {});
            try kept.append(arena, r);
        }
        table.rows = kept;
    }

    // Fill NA
    if (opts.fill_na) |s| try applyFillNa(arena, &table, s);

    // Reports (stderr)
    if (opts.detect_types) try reportTypes(arena, &table, errw);
    if (opts.outlier_method != null) try reportOutliers(arena, &table, opts, errw);
    if (opts.validations.len > 0) {
        try errw.print("# validation report\n", .{});
        validation_failures = try runValidations(&table, opts, errw);
    }

    // Write output
    if (table.header) |h| {
        try writeRow(out, &.{ .fields = h }, opts.delimiter);
    }
    for (table.rows.items) |r| try writeRow(out, &r, opts.delimiter);

    if (opts.stats) {
        try errw.print("# stats\n", .{});
        try errw.print("  rows out: {d}\n", .{table.rows.items.len});
        try errw.print("  cols: {d}\n", .{table.columnCount()});
        try errw.print("  validation failures: {d}\n", .{validation_failures});
    }

    return validation_failures;
}

// =============================================================================
// Entrypoint
// =============================================================================

pub fn main() !void {
    var gpa_state = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa_state.deinit();
    const gpa = gpa_state.allocator();

    var arena_state = std.heap.ArenaAllocator.init(gpa);
    defer arena_state.deinit();
    const arena = arena_state.allocator();

    const args = try std.process.argsAlloc(gpa);
    defer std.process.argsFree(gpa, args);

    const opts = parseArgs(arena, args) catch |err| {
        std.debug.print("Run with --help for usage.\n", .{});
        return err;
    };

    var stdout_buf: [16 * 1024]u8 = undefined;
    var stdout_writer = std.fs.File.stdout().writer(&stdout_buf);
    const stdout = &stdout_writer.interface;

    var stderr_buf: [4096]u8 = undefined;
    var stderr_writer = std.fs.File.stderr().writer(&stderr_buf);
    const stderr = &stderr_writer.interface;

    if (opts.input_path) |p| {
        if (std.mem.eql(u8, p, "__HELP__")) {
            try printHelp(stdout);
            try stdout.flush();
            return;
        }
        if (std.mem.eql(u8, p, "__VERSION__")) {
            try stdout.print("dataclean {s}\n", .{VERSION});
            try stdout.flush();
            return;
        }
    }

    // Optional file output
    var file_writer_opt: ?std.fs.File.Writer = null;
    var out_file: ?std.fs.File = null;
    var out: *std.Io.Writer = stdout;
    var out_buf: [16 * 1024]u8 = undefined;
    if (opts.output_path) |p| {
        const f = try std.fs.cwd().createFile(p, .{});
        out_file = f;
        file_writer_opt = f.writer(&out_buf);
        out = &file_writer_opt.?.interface;
    }
    defer if (out_file) |f| f.close();

    const raw = try readAll(gpa, opts.input_path);
    defer gpa.free(raw);

    const failures = try runPipeline(gpa, arena, raw, &opts, out, stderr);

    try out.flush();
    try stderr.flush();

    if (opts.strict and failures > 0) {
        std.process.exit(1);
    }
}

// =============================================================================
// Tests
// =============================================================================

const testing = std.testing;

test "stripBom strips UTF-8 BOM only when present" {
    const with_bom = "\xEF\xBB\xBFhello";
    try testing.expectEqualStrings("hello", stripBom(with_bom));
    try testing.expectEqualStrings("hello", stripBom("hello"));
    try testing.expectEqualStrings("", stripBom(""));
}

test "normalizeEol converts CRLF and lone CR to LF" {
    var arena = std.heap.ArenaAllocator.init(testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();

    const got1 = try normalizeEol(a, "a\r\nb\rc\nd");
    try testing.expectEqualStrings("a\nb\nc\nd", got1);

    const got2 = try normalizeEol(a, "no-newline");
    try testing.expectEqualStrings("no-newline", got2);
}

test "parseCsv handles quoted fields, escaped quotes, embedded newlines" {
    var arena = std.heap.ArenaAllocator.init(testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();

    const input = "a,b,c\n\"hello, world\",\"line1\nline2\",\"a\"\"b\"\n";
    const result = try parseCsv(a, input, ',');
    try testing.expectEqual(@as(usize, 2), result.rows.items.len);

    try testing.expectEqual(@as(usize, 3), result.rows.items[0].fields.len);
    try testing.expectEqualStrings("a", result.rows.items[0].fields[0]);

    try testing.expectEqual(@as(usize, 3), result.rows.items[1].fields.len);
    try testing.expectEqualStrings("hello, world", result.rows.items[1].fields[0]);
    try testing.expectEqualStrings("line1\nline2", result.rows.items[1].fields[1]);
    try testing.expectEqualStrings("a\"b", result.rows.items[1].fields[2]);
}

test "parseCsv preserves trailing row without newline" {
    var arena = std.heap.ArenaAllocator.init(testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();

    const result = try parseCsv(a, "x,y\n1,2", ',');
    try testing.expectEqual(@as(usize, 2), result.rows.items.len);
    try testing.expectEqualStrings("1", result.rows.items[1].fields[0]);
    try testing.expectEqualStrings("2", result.rows.items[1].fields[1]);
}

test "transformCell trim + collapse-ws + lowercase + null normalization" {
    var arena = std.heap.ArenaAllocator.init(testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();

    var opts = Options{};
    opts.trim = true;
    opts.collapse_ws = true;
    opts.lowercase = true;

    const r1 = try transformCell(a, "   FOO    BAR   ", &opts);
    try testing.expectEqualStrings("foo bar", r1);

    opts.normalize_nulls = true;
    const r2 = try transformCell(a, " N/A ", &opts);
    try testing.expectEqualStrings("", r2);
}

test "transformCell smart quotes + control strip" {
    var arena = std.heap.ArenaAllocator.init(testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();

    var opts = Options{};
    opts.smart_quotes = true;
    opts.strip_control = true;

    // "hello" with curly double quotes (U+201C, U+201D)
    const input = "\xE2\x80\x9Chello\xE2\x80\x9D";
    const r = try transformCell(a, input, &opts);
    try testing.expectEqualStrings("\"hello\"", r);

    // control bytes (NUL, BEL) stripped, tab kept
    const input2 = "a\x00b\tc\x07";
    const r2 = try transformCell(a, input2, &opts);
    try testing.expectEqualStrings("ab\tc", r2);
}

test "detectCellType + mergeTypes" {
    try testing.expectEqual(ColType.empty, detectCellType(""));
    try testing.expectEqual(ColType.integer, detectCellType("42"));
    try testing.expectEqual(ColType.integer, detectCellType("-7"));
    try testing.expectEqual(ColType.float, detectCellType("3.14"));
    try testing.expectEqual(ColType.float, detectCellType("1e3"));
    try testing.expectEqual(ColType.boolean, detectCellType("true"));
    try testing.expectEqual(ColType.boolean, detectCellType("FALSE"));
    try testing.expectEqual(ColType.string, detectCellType("hello"));

    try testing.expectEqual(ColType.integer, mergeTypes(.integer, .integer));
    try testing.expectEqual(ColType.float, mergeTypes(.integer, .float));
    try testing.expectEqual(ColType.float, mergeTypes(.float, .integer));
    try testing.expectEqual(ColType.string, mergeTypes(.integer, .string));
    try testing.expectEqual(ColType.integer, mergeTypes(.empty, .integer));
}

test "percentile linear interpolation" {
    const data = [_]f64{ 1, 2, 3, 4, 5 };
    try testing.expectApproxEqAbs(@as(f64, 1), percentile(&data, 0), 1e-9);
    try testing.expectApproxEqAbs(@as(f64, 3), percentile(&data, 0.5), 1e-9);
    try testing.expectApproxEqAbs(@as(f64, 5), percentile(&data, 1), 1e-9);
    try testing.expectApproxEqAbs(@as(f64, 2), percentile(&data, 0.25), 1e-9);
}

test "computeMean and computeStdDev" {
    const data = [_]f64{ 2, 4, 4, 4, 5, 5, 7, 9 };
    const mean = computeMean(&data);
    try testing.expectApproxEqAbs(@as(f64, 5), mean, 1e-9);
    const sd = computeStdDev(&data, mean);
    // sample stddev = sqrt(32/7) ≈ 2.13809
    try testing.expectApproxEqAbs(@as(f64, 2.138089935299395), sd, 1e-9);
}

test "rowHash is order-sensitive and field-sensitive" {
    var arena = std.heap.ArenaAllocator.init(testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();

    const f1 = [_][]u8{ try a.dupe(u8, "x"), try a.dupe(u8, "y") };
    const f2 = [_][]u8{ try a.dupe(u8, "x"), try a.dupe(u8, "y") };
    const f3 = [_][]u8{ try a.dupe(u8, "y"), try a.dupe(u8, "x") };

    const r1 = Row{ .fields = @constCast(&f1) };
    const r2 = Row{ .fields = @constCast(&f2) };
    const r3 = Row{ .fields = @constCast(&f3) };

    try testing.expectEqual(rowHash(&r1, ','), rowHash(&r2, ','));
    try testing.expect(rowHash(&r1, ',') != rowHash(&r3, ','));
}

test "writeCell quotes only when needed" {
    var buf: [256]u8 = undefined;
    var w = std.Io.Writer.fixed(&buf);

    try writeCell(&w, "plain", ',');
    try testing.expectEqualStrings("plain", w.buffered());

    var buf2: [256]u8 = undefined;
    var w2 = std.Io.Writer.fixed(&buf2);
    try writeCell(&w2, "has,comma", ',');
    try testing.expectEqualStrings("\"has,comma\"", w2.buffered());

    var buf3: [256]u8 = undefined;
    var w3 = std.Io.Writer.fixed(&buf3);
    try writeCell(&w3, "say \"hi\"", ',');
    try testing.expectEqualStrings("\"say \"\"hi\"\"\"", w3.buffered());
}
