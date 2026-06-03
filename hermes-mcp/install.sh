#!/usr/bin/env bash
# Install Hermes MCP on a Raspberry Pi (or dev machine).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
MANUAL_ROOT="${HERMES_MANUAL_ROOT:-$(dirname "$ROOT")/manual}"

python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"

if [[ -d "$MANUAL_ROOT" ]]; then
  HERMES_MANUAL_ROOT="$MANUAL_ROOT" "$ROOT/.venv/bin/python" "$ROOT/index_manual.py" --rebuild \
    --manual-root "$MANUAL_ROOT" \
    --db "$ROOT/data/manual.db"
else
  echo "manual/ not found at $MANUAL_ROOT — copy manual before indexing" >&2
fi

echo ""
echo "Add to your MCP client config (see mcp-config.example.json):"
echo "  command: $ROOT/.venv/bin/python"
echo "  args: [$ROOT/server.py]"
echo "  env: HERMES_MANUAL_DB=$ROOT/data/manual.db"
echo "       HERMES_MANUAL_ROOT=$MANUAL_ROOT"
echo "       HERMES_VEHICLE_STATE=/var/run/hermes/vehicle_state.json"