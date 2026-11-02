#!/usr/bin/env bash
set -euo pipefail
work=/root/private_data/mj/xiangshan
payload=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$work"
log=$(mktemp -d "$work/evidence/vdot-mtval-build-XXXXXX")
printf 'LOG_DIR=%s\n' "$log"
cp "$payload/pinned.sha256" "$log/pinned.sha256"
finish() {
  local rc=$?
  trap - EXIT
  set +e
  sha256sum -c "$log/pinned.sha256" > "$log/identities-after.txt" 2>&1
  local ids=$?
  if ((ids != 0)); then cat "$log/identities-after.txt"; rc=9; fi
  printf 'IDENTITIES_AFTER_EXIT=%s\nVDOT_MTVAL_EXIT=%s\nLOG_DIR=%s\n' "$ids" "$rc" "$log" | tee "$log/result.txt"
  if ((rc == 0)); then echo VDOT_MTVAL_ACCEPTANCE_PASS | tee -a "$log/result.txt"; fi
  exit "$rc"
}
trap finish EXIT
sha256sum -c "$log/pinned.sha256" | tee "$log/identities-before.txt"
# Verify the previously accepted overlap image using its saved original identity.
sha256sum -c "$work/evidence/vdot-matrix-OMcrpf/vdot-overlap/identity.sha256" > "$log/overlap-original-identity.txt"
ps -eo pid,comm > "$log/processes.txt"
if awk '$2 ~ /^(emu|java|mill|make|verilator_bin)$/ {print; found=1} END {exit !found}' "$log/processes.txt"; then
  echo STOP_EXISTING_BUILD_OR_SIMULATION; exit 3
fi
test ! -e "$work/vdot-mtval-fix-20261024"
python3 - "$work" <<'PY'
import shutil,sys
free=shutil.disk_usage(sys.argv[1]).free
print('FREE_GIB=%.1f' % (free/2**30))
if free < 20*2**30: raise SystemExit('STOP: fresh source/build requires at least 20 GiB free; do not delete old evidence')
PY
{
  date -Iseconds
  df -h "$work"
  for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory/memory.limit_in_bytes /sys/fs/cgroup/cpu/cpu.cfs_quota_us /sys/fs/cgroup/cpu/cpu.cfs_period_us; do
    if [[ -r "$f" ]]; then printf '%s=' "$f"; cat "$f" || true; fi
  done
} > "$log/resources.txt"
source "$work/env-toolchain.sh"
xs="$work/vdot-mtval-fix-20261024/XiangShan"
ref="$work/vdot-dev-20261024/NEMU/build/riscv64-nemu-interpreter-so"
flash="$work/evidence/vdot-build-80mKCD/boot-flash.bin"
export NOOP_HOME="$xs" NEMU_HOME="$work/vdot-dev-20261024/NEMU"
export COURSIER_REPOSITORIES=https://repo.maven.apache.org/maven2
agent="$work/evidence/mill-proxy-G1cURV/proxy-agent.jar"
test -s "$agent"
export JAVA_TOOL_OPTIONS="-javaagent:$agent"
printf 'CONFIG=MinimalConfig\nNUM_CORES=1\nEMU_TRACE=1\nJVM_XMX=6G\nNOOP_HOME=%s\nNEMU_HOME=%s\n' "$NOOP_HOME" "$NEMU_HOME" > "$log/build-environment.txt"
stage() {
  local name=$1; shift
  printf 'START=%s STAGE=%s\n' "$(date -Iseconds)" "$name"
  printf '%q ' "$@" > "$log/$name.argv"; printf '\n' >> "$log/$name.argv"
  set +e
  "$@" > "$log/$name.log" 2>&1
  local rc=$?
  set -e
  printf '%s\n' "$rc" > "$log/$name.exit"
  printf 'STAGE=%s EXIT=%s END=%s\n' "$name" "$rc" "$(date -Iseconds)"
  if ((rc != 0)); then tail -n 65 "$log/$name.log"; exit "$rc"; fi
}
stage apply python3 "$payload/apply_scnet_vdot_mtval.py" "$log"
# No NEMU configuration/build and no application rebuild. Only the fresh core.
stage emu-build timeout -k 60s 14400s make -C "$xs" emu CONFIG=MinimalConfig NUM_CORES=1 EMU_TRACE=1 \
  JVM_XMX=6G NO_DIFF=0 RELEASE=0 PLDM=0 EMU_THREADS=0 REMOTE=localhost \
  CC=/usr/lib/llvm-19/bin/clang CXX=/usr/lib/llvm-19/bin/clang++ -j4
emu="$xs/build/emu"
stage emu-help timeout -k 5s 30s "$emu" --help
sha256sum "$emu" "$ref" > "$log/new-emu-reference.sha256"
cat "$log/new-emu-reference.sha256"
# The original failing case is second in this unchanged exception image.
for app in vdot-exceptions vdot-overlap vdot-smoke hello-meijie vadd4; do
  case "$app" in
    vdot-exceptions) img="$work/vdot-dev-20261024/nexus-am/apps/$app/build/$app-riscv64-xs.bin"; marker='PASS VDOT_EXCEPTIONS cases=64 traps=62 legal=2';;
    vdot-overlap) img="$work/vdot-dev-20261024/nexus-am/apps/$app/build/$app-riscv64-xs.bin"; marker='PASS VDOT_OVERLAP cases=60 partitions=15';;
    vdot-smoke) img="$work/vdot-dev-20261024/nexus-am/apps/$app/build/$app-riscv64-xs.bin"; marker='PASS VDOT_SMOKE cases=7';;
    hello-meijie) img="$work/sources/nexus-am-learning/apps/$app/build/$app-riscv64-xs.bin"; marker='hello xiangshan, I am Meijie, IP address:';;
    vadd4) img="$work/sources/nexus-am-learning/apps/$app/build/$app-riscv64-xs.bin"; marker='PASS: vadd.vv produced [11, 22, 33, 44]';;
  esac
  run="$log/$app"; mkdir -p "$run/build"
  export NOOP_HOME="$run"
  printf 'NOOP_HOME=%s\n' "$NOOP_HOME" > "$run/environment.txt"
  sha256sum "$emu" "$ref" "$img" "$flash" > "$run/identity.sha256"
  printf 'Running %s; log=%s/%s.log (limit 1800 seconds)\n' "$app" "$log" "$app"
  stage "$app" timeout -k 10s 1800s "$emu" -i "$img" "--diff=$ref" \
    -F "$flash" --seed=1 --max-cycles=3000000 --no-snapshot
  for expected in "The reference model is $ref" 'Difftest enabled.' 'HIT GOOD TRAP' "$marker"; do
    if ! grep -aFq -- "$expected" "$log/$app.log"; then echo "MISSING=$expected"; tail -n 40 "$log/$app.log"; exit 4; fi
  done
  if grep -aE 'FAIL|HIT BAD TRAP|ABORT|different at pc' "$log/$app.log"; then exit 5; fi
  grep -aE 'The reference model|Difftest enabled|PASS VDOT_|HIT GOOD TRAP|PASS: vadd' "$log/$app.log" | tail -n 8
  printf 'ACCEPTED=%s\n' "$app"
done
