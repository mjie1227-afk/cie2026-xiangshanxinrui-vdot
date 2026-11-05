#!/usr/bin/env bash
# Explicit stages; no full-core build starts during 'check'.
set -euo pipefail
vdot_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$vdot_root"
vdot_stage=${1:-help}
case "$vdot_stage" in check|build|smoke|functional|performance) ;;
  *) echo 'Usage: bash tools/reproduce.sh check|build|smoke|functional|performance'; exit 2;;
esac
mkdir -p work
exec 9>work/reproduce.lock
flock -n 9 || { echo 'Another reproduce.sh is running in this repository.'; exit 2; }
if [[ ! -f work/build/vdot-restored.json ]]; then
  python3 tools/prepare_sources.py
fi
if [[ "$vdot_stage" == check || "$vdot_stage" == build ]]; then
  python3 tools/check_env.py
fi
if [[ "$vdot_stage" == build ]]; then
  bash tools/build.sh "$PWD/work/build" nemu
  bash tools/build.sh "$PWD/work/build" emu
fi
if [[ "$vdot_stage" == smoke || "$vdot_stage" == functional || "$vdot_stage" == performance ]]; then
  test -x work/build/XiangShan/build/emu || { echo 'Missing emu; run build first.'; exit 2; }
  test -f work/build/NEMU/build/riscv64-nemu-interpreter-so || { echo 'Missing NEMU reference; run build first.'; exit 2; }
  vdot_case_list=$(python3 tools/verify_results.py --list "$vdot_stage")
  mapfile -t vdot_cases <<< "$vdot_case_list"
  vdot_tag=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
  vdot_suite_dir="$PWD/runs/$vdot_stage-$vdot_tag"
  printf 'SUITE_DIRECTORY=%s\n' "$vdot_suite_dir"
  for vdot_case in "${vdot_cases[@]}"; do
    bash tools/build.sh "$PWD/work/build" app "$vdot_case"
    python3 tools/run_case.py "$vdot_case" \
      --emu "$PWD/work/build/XiangShan/build/emu" \
      --reference "$PWD/work/build/NEMU/build/riscv64-nemu-interpreter-so" \
      --image "$PWD/work/build/nexus-am/apps/$vdot_case/build/$vdot_case-riscv64-xs.bin" \
      --output "$vdot_suite_dir/$vdot_case" \
      --max-cycles 20000000 --timeout 7200
  done
  python3 tools/verify_results.py --suite "$vdot_stage" --directory "$vdot_suite_dir"
fi
printf 'REPRODUCE_STAGE=%s PASS\n' "$vdot_stage"
