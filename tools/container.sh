#!/usr/bin/env bash
# Bash compatibility entry; Windows uses python tools/container.py directly.
set -euo pipefail
vdot_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$vdot_root"
exec python3 tools/container.py "$@"
