#!/usr/bin/env bash
set -euo pipefail
work=/root/private_data/mj/xiangshan
package="$work/evidence/vdot-load-package-Dxbuvr/package"
retry_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$work"

exec 9>"$work/evidence/vdot-software-bench.lock"
if ! flock -n 9; then
    printf 'OPT_SCRIPT_EXIT=75\nAnother benchmark is running; stop.\n' \
        > "$retry_dir/exit-status.txt"
    exit 75
fi

set +e
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$package" \
    python3 -u "$retry_dir/resume-run.py" "$package" "$retry_dir" \
    > "$retry_dir/console.log" 2>&1
rc=$?
set -e

printf 'OPT_SCRIPT_EXIT=%s\nLOG_DIR=%s\n' "$rc" "$retry_dir" \
    > "$retry_dir/exit-status.txt"
exit "$rc"
