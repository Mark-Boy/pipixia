#!/usr/bin/env bash
# Build the dataclean binary in release mode.
# Usage:
#   bash scripts/install.sh             # builds zig-out/bin/dataclean
#   PREFIX=$HOME/.local bash scripts/install.sh   # also installs to $PREFIX/bin

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL_DIR"

if ! command -v zig >/dev/null 2>&1; then
    echo "error: zig not found in PATH" >&2
    exit 1
fi

ZIG_VER="$(zig version)"
echo "using zig $ZIG_VER"

zig build -Doptimize=ReleaseFast

BIN="$SKILL_DIR/zig-out/bin/dataclean"
if [[ ! -x "$BIN" ]]; then
    echo "error: build did not produce $BIN" >&2
    exit 1
fi

echo "built: $BIN"
"$BIN" --version

if [[ -n "${PREFIX:-}" ]]; then
    mkdir -p "$PREFIX/bin"
    cp "$BIN" "$PREFIX/bin/dataclean"
    echo "installed: $PREFIX/bin/dataclean"
fi
