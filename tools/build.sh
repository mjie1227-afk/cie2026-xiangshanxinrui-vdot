#!/usr/bin/env bash
# Explicit, logged build steps for a fresh source tree prepared by restore_sources.py.
set -euo pipefail
vdot_work=$(realpath "${1:?Usage: build.sh WORKDIR nemu|emu|app [APP]}")
vdot_kind=${2:?Choose nemu, emu or app}
test -f "$vdot_work/vdot-restored.json" || { echo 'Expected a tree created by restore_sources.py'; exit 2; }
export NOOP_HOME="$vdot_work/XiangShan" NEMU_HOME="$vdot_work/NEMU" AM_HOME="$vdot_work/nexus-am"
export COURSIER_REPOSITORIES="${COURSIER_REPOSITORIES:-https://repo.maven.apache.org/maven2}"
mkdir -p "$vdot_work/build-logs"
vdot_log=$(mktemp -d "$vdot_work/build-logs/${vdot_kind}-XXXXXX")
printf 'BUILD_LOG=%s\n' "$vdot_log"
case "$vdot_kind" in
 nemu) vdot_argv=(make -C "$NEMU_HOME" -j"${VDOT_JOBS:-4}");;
 emu)
   vdot_cc=${VDOT_CC:-$(command -v clang-19 || command -v clang)}
   vdot_cxx=${VDOT_CXX:-$(command -v clang++-19 || command -v clang++)}
   vdot_argv=(make -C "$NOOP_HOME" emu CONFIG=MinimalConfig NUM_CORES=1 EMU_TRACE=1 JVM_XMX=6G NO_DIFF=0 RELEASE=0 PLDM=0 EMU_THREADS=0 REMOTE=localhost "CC=$vdot_cc" "CXX=$vdot_cxx" -j"${VDOT_JOBS:-4}");;
 app)
   vdot_app=${3:?Specify an application name}
   case "$vdot_app" in *[!a-zA-Z0-9_-]*|'') echo 'Invalid application name'; exit 2;; esac
   test -f "$AM_HOME/apps/$vdot_app/Makefile"
   vdot_riscv_cc=${VDOT_RISCV_CC:-$(command -v riscv64-linux-gnu-gcc-12 || command -v riscv64-linux-gnu-gcc)}
   vdot_argv=(make -C "$AM_HOME/apps/$vdot_app" image ARCH=riscv64-xs LINUX_GNU_TOOLCHAIN=1 MARCH=rv64gcv "CC=$vdot_riscv_cc" "AS=$vdot_riscv_cc" -j"${VDOT_APP_JOBS:-2}");;
 *) echo 'Choose nemu, emu or app'; exit 2;;
esac
{
 date -Iseconds
 printf 'PWD=%s\nNOOP_HOME=%s\nNEMU_HOME=%s\nAM_HOME=%s\n' "$PWD" "$NOOP_HOME" "$NEMU_HOME" "$AM_HOME"
 printf '%q ' "${vdot_argv[@]}"; printf '\n'
 uname -a
 java -version 2>&1 || true
 verilator --version || true
 make --version | head -n 1
 for vdot_tool in "${vdot_cc:-}" "${vdot_cxx:-}" "${vdot_riscv_cc:-}"; do
   if [[ -n "$vdot_tool" ]]; then "$vdot_tool" --version | head -n 1; fi
 done
} > "$vdot_log/environment.txt"
set +e
"${vdot_argv[@]}" > "$vdot_log/build.log" 2>&1
vdot_rc=$?
set -e
printf '%s\n' "$vdot_rc" > "$vdot_log/exit-code.txt"
printf 'BUILD_EXIT_CODE=%s\nBUILD_LOG=%s\n' "$vdot_rc" "$vdot_log"
if (( vdot_rc != 0 )); then tail -n 35 "$vdot_log/build.log"; fi
exit "$vdot_rc"
