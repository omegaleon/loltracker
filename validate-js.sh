#!/bin/bash
# validate-js.sh — Catch undefined function calls in app.js before they ship.
# Runs automatically as a pre-commit hook, or manually: ./validate-js.sh
#
# Exit code 0 = clean, 1 = problems found (blocks commit)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JS_FILE="$SCRIPT_DIR/static/app.js"

if [ ! -f "$JS_FILE" ]; then
  echo "ERROR: $JS_FILE not found"
  exit 1
fi

if ! command -v node &> /dev/null; then
  echo "WARNING: node not found, skipping validation"
  exit 0
fi

# Syntax check
if ! node -c "$JS_FILE" 2>&1; then
  echo ""
  echo "=========================================="
  echo " JS SYNTAX ERROR — commit blocked"
  echo "=========================================="
  exit 1
fi

# Undefined function check
exec node "$SCRIPT_DIR/validate-js.js"
