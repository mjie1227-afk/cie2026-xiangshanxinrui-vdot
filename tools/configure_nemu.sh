#!/usr/bin/env bash
# Generate headers from the prepared .config; never replace it with a defconfig.
set -euo pipefail
export NEMU_HOME=$(realpath "${1:?Usage: configure_nemu.sh NEMU_DIRECTORY}")
test -f "$NEMU_HOME/.config"
make -C "$NEMU_HOME/tools/kconfig" NAME=conf
make -C "$NEMU_HOME/tools/fixdep"
cd "$NEMU_HOME"
tools/kconfig/build/conf --syncconfig Kconfig < /dev/null
test -s include/config/auto.conf
test -s include/generated/autoconf.h
printf 'NEMU_CONFIG_OK\n'
