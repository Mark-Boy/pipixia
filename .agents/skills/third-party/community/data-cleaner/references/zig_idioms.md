# Zig 0.15.2 Idioms Reference

Verified patterns for Zig 0.15.2 (October 2025). Major breaking changes from 0.13–0.15: I/O system rewritten, ArrayList is unmanaged by default, type reflection tags are lowercase.

## 1. Main Skeleton with Modern stdout

```zig
const std = @import("std");

pub fn main() !void {
    var stdout_buf: [1024]u8 = undefined;
    var stdout_writer = std.fs.File.stdout().writer(&stdout_buf);
    const stdout = &stdout_writer.interface;
    
    try stdout.print("Hello, world!\n", .{});
    try stdout.flush();  // Critical: always flush before exit
}
```

**Key points:** In 0.15.2, `std.fs.File.stdout().writer()` requires an explicit buffer; data goes to the buffer first, then must be flushed. Unbuffered pattern uses `&.{}` (empty slice) as buffer, but buffered is preferred for performance.

---

## 2. Reading All of stdin into a Buffer

```zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const stdin = std.fs.File.stdin();
    const input = try stdin.readToEndAlloc(allocator, 65536);
    defer allocator.free(input);

    // Process `input` ([]u8)
}
```

**Key points:** Use `std.fs.File.stdin()` (not `std.io.getStdIn()`). Call `readToEndAlloc(allocator, max_size)` on the File directly. In 0.15, Reader does not have `readAllAlloc`; use File's method instead.

---

## 3. Reading a File by Path into Memory

```zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const file = try std.fs.cwd().openFile("data.csv", .{});
    defer file.close();
    
    const data = try file.readToEndAlloc(allocator, 1024 * 1024);
    defer allocator.free(data);

    // Process `data` ([]u8)
}
```

**Key points:** Open with `cwd().openFile()`, then call `readToEndAlloc()`. Max size is the second argument; reads fail if file exceeds it.

---

## 4. Writing to stdout Buffered

```zig
const std = @import("std");

pub fn main() !void {
    var stdout_buf: [4096]u8 = undefined;
    var stdout_writer = std.fs.File.stdout().writer(&stdout_buf);
    const stdout = &stdout_writer.interface;

    try stdout.print("Name: {s}\n", .{"Alice"});
    try stdout.print("Count: {d}\n", .{42});
    
    try stdout.flush();  // Flush after all writes
}
```

**Key points:** Buffer size depends on use case; 4096 bytes is typical. Always call `flush()` explicitly. The `.interface` field is the writer interface used for `print()` and other methods.

---

## 5. ArrayList(u8) and ArrayList(T)

```zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // ArrayList(u8) for bytes
    var buffer = std.ArrayList(u8){};
    defer buffer.deinit(allocator);
    
    try buffer.append(allocator, 'H');
    try buffer.appendSlice(allocator, "ello");
    
    const items: []u8 = buffer.items;  // Access underlying slice
    std.debug.print("{s}\n", .{items});

    // ArrayList(T) with custom type
    var numbers = std.ArrayList(i32){};
    defer numbers.deinit(allocator);
    
    try numbers.append(allocator, 100);
    for (numbers.items) |num| {
        _ = num;  // Process
    }
}
```

**Key points:** In 0.15, ArrayList does not store the allocator internally. Every `append()`, `appendSlice()`, and `deinit()` call requires passing the allocator explicitly. `.items` is the slice of all elements. Initialize as `std.ArrayList(T){}` (not `.empty` literal).

---

## 6. HashMap and StringHashMap

```zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // StringHashMap (string keys)
    var map = std.StringHashMap(i32).init(allocator);
    defer map.deinit();

    try map.put("age", 30);
    try map.put("score", 95);

    if (map.get("age")) |val| {
        std.debug.print("Age: {d}\n", .{val});
    }

    if (map.contains("score")) {
        // Key exists
    }

    // AutoHashMap (any type as key)
    var counts = std.AutoHashMap(u32, i32).init(allocator);
    defer counts.deinit();
    
    try counts.put(1, 100);
}
```

**Key points:** `init(allocator)` is required. `put()`, `get()`, `contains()` do not require allocator as argument (allocator is stored in the HashMap internally). Call `deinit()` to free resources. For StringHashMap, string keys must remain valid for the map's lifetime.

---

## 7. std.fmt.parseInt and parseFloat

```zig
const std = @import("std");

pub fn main() !void {
    // Parse integers (base 10)
    const count = try std.fmt.parseInt(i32, "42", 10);
    std.debug.print("{d}\n", .{count});

    // Parse with auto-detected base (0b, 0o, 0x prefixes)
    const num = try std.fmt.parseInt(u64, "0xFF", 0);
    _ = num;

    // Parse floats
    const pi = try std.fmt.parseFloat(f64, "3.14159");
    std.debug.print("{d}\n", .{pi});

    // Error handling
    std.fmt.parseInt(i32, "not_a_number", 10) catch |err| {
        std.debug.print("Parse error: {}\n", .{err});
    };
}
```

**Key points:** 
- `parseInt(T, string, base)` – base 0 auto-detects (0b→2, 0o→8, 0x→16, else 10)
- `parseFloat(T, string)` – handles scientific notation (1e3), nan, inf
- Both return error types; use `try` or `catch`
- Integer overflow and invalid characters → error

---

## 8. String Splitting: tokenizeScalar / tokenizeSequence / tokenizeAny

```zig
const std = @import("std");

pub fn main() !void {
    // Split on single character (comma-separated values)
    var csv_iter = std.mem.tokenizeScalar(u8, "a,b,c", ',');
    while (csv_iter.next()) |field| {
        std.debug.print("Field: {s}\n", .{field});
    }

    // Split on substring (multi-char delimiter)
    var delim_iter = std.mem.tokenizeSequence(u8, "a<>b<>c", "<>");
    while (delim_iter.next()) |part| {
        std.debug.print("Part: {s}\n", .{part});
    }

    // Split on any character in a set
    var any_iter = std.mem.tokenizeAny(u8, "a,b;c", ",;");
    while (any_iter.next()) |token| {
        std.debug.print("Token: {s}\n", .{token});
    }
}
```

**Key points:**
- `tokenizeScalar(u8, string, delimiter_byte)` – single-char delimiter, skips empty results
- `tokenizeSequence(u8, string, delimiter_string)` – multi-char delimiter, skips empty results
- `tokenizeAny(u8, string, char_set)` – split on any char in the set, skips empty results
- `splitScalar`/`splitSequence` equivalents exist but include empty results (use tokenize for CSV/fields)

---

## 9. Command-Line Arguments

```zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    for (args, 0..) |arg, i| {
        std.debug.print("argv[{d}] = {s}\n", .{i, arg});
    }
}
```

**Key points:** `argsAlloc(allocator)` returns `[][]u8` (array of strings). Must call `argsFree(allocator, args)` to clean up. `args[0]` is the program name. No hidden allocations in Zig, so explicit deallocation is required.

---

## 10. build.zig Skeleton (0.15.2)

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "dataclean",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });

    b.installArtifact(exe);

    const run_cmd = b.addRunArtifact(exe);
    const run_step = b.step("run", "Run the application");
    run_step.dependOn(&run_cmd.step);

    if (b.args) |args| {
        run_cmd.addArgs(args);
    }
}
```

**Key points:**
- `standardTargetOptions()` and `standardOptimizeOption()` expose CLI flags
- **Critical in 0.15.2:** Use `root_module = b.createModule()` pattern, not `root_source_file` directly
- `b.path()` resolves paths relative to build.zig
- `b.installArtifact()` places binary in `zig-out/bin/`
- `b.addRunArtifact()` + `b.step()` enables `zig build run`
- Pass CLI args via `addArgs()` for `zig build run -- arg1 arg2`

---

## Allocator Setup (GeneralPurposeAllocator)

```zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Use allocator for all dynamic allocations
    const data = try allocator.alloc(u8, 256);
    defer allocator.free(data);
}
```

**Key points:** GeneralPurposeAllocator detects leaks in debug builds. `defer _ = gpa.deinit()` is idiomatic. For testing, use `std.testing.allocator`.

---

## Common Error Types (0.15.2)

- `ParseError` → `parseInt()`/`parseFloat()` failure
- `FileNotFound`, `AccessDenied` → file operations
- `OutOfMemory` → allocator exhaustion
- `StreamTooLong` → read exceeds max size

Use `try` for early exit, `catch` for custom handling.
