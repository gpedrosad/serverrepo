#!/bin/bash
# extract-core.sh — analyze a core dump from the yurots server.
#
# Usage (on the VPS):
#   ./scripts/extract-core.sh /path/to/core
#   ./scripts/extract-core.sh                    # auto-detect newest core
#
# The script:
#   1) Locates the yurots binary (the binary the core was made from)
#   2) Runs `gdb` to print:
#        - all threads' backtraces
#        - registers
#        - info about the crash point
#   3) Saves the report to data/crash-report-<timestamp>.txt
#
# Requirements:
#   - gdb installed (apt-get install gdb)
#   - The yurots binary must be the SAME one that crashed (matching build)
#   - The core must have been written with the same working directory as
#     the binary was running in (so symbols resolve)

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
YUROTS_BIN="$PROJECT_ROOT/server/YurOTS/ots/source/yurots"

#Auto-detect newest core if not provided.
if [ $# -lt 1 ]; then
    # Search in likely locations: data/ in the project, and the bind-mount
    # /cores if present.
    search_paths=(
        "$PROJECT_ROOT/server/YurOTS/ots"
        "$PROJECT_ROOT/server/YurOTS/ots/data"
        "/cores"
    )
    for p in "${search_paths[@]}"; do
        if [ -d "$p" ]; then
            found=$(ls -t "$p"/core* 2>/dev/null | head -n 1 || true)
            if [ -n "$found" ]; then
                CORE="$found"
                break
            fi
        fi
    done
    if [ -z "${CORE:-}" ]; then
        echo "ERROR: no core file found in expected locations."
        echo "Searched: ${search_paths[*]}"
        echo "Pass the core file as the first argument: $0 /path/to/core"
        exit 1
    fi
    echo "Auto-detected core: $CORE"
else
    CORE="$1"
fi

if [ ! -f "$CORE" ]; then
    echo "ERROR: core file not found: $CORE"
    exit 1
fi

if [ ! -x "$YUROTS_BIN" ]; then
    echo "ERROR: yurots binary not found or not executable: $YUROTS_BIN"
    echo "Make sure the binary is the one that produced the core."
    exit 1
fi

REPORT_DIR="$PROJECT_ROOT/server/YurOTS/ots/data"
mkdir -p "$REPORT_DIR"
TS=$(date -u +%Y%m%d-%H%M%S)
REPORT="$REPORT_DIR/gdb-report-$TS.txt"

echo "Binary: $YUROTS_BIN"
echo "Core:   $CORE"
echo "Report: $REPORT"
echo "---"

#Run gdb in batch mode. The commands print all threads' backtraces and info.
gdb -q -batch \
    -ex "set pagination off" \
    -ex "set print pretty on" \
    -ex "thread apply all bt full" \
    -ex "info registers" \
    -ex "info threads" \
    -ex "disassemble \$pc, +32" \
    -ex "quit" \
    "$YUROTS_BIN" "$CORE" > "$REPORT" 2>&1 || true

#Show a summary on stdout.
echo ""
echo "=== Summary (first 60 lines of $REPORT) ==="
head -n 60 "$REPORT"
echo ""
echo "=== Full report at: $REPORT ==="
echo "Lines: $(wc -l < "$REPORT")"
