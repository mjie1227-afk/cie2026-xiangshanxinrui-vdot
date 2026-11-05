"""Pre-build checks for this repository. No installation or full-core build."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
from checkpoint_toolchain import prepare as prepare_checkpoint_toolchain

ROOT = Path(__file__).resolve().parents[1]


def choose(variable, candidates):
    # Same selection order as tools/build.sh.
    return os.environ.get(variable) or next(
        (shutil.which(c) for c in candidates if shutil.which(c)), candidates[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, default=ROOT / 'work/build')
    args = ap.parse_args()
    if sys.platform != 'linux' or sys.version_info < (3, 9):
        print('ENV_CHECK=FAIL: Linux and Python >= 3.9 required.'); return 2
    work = args.work.expanduser().resolve()
    base = ROOT / 'work/environment-checks'
    base.mkdir(parents=True, exist_ok=True)
    log = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=base))
    checks, errors, warnings = [], [], []
    print('REPOSITORY=' + str(ROOT), flush=True)
    print('BUILD_WORK=' + str(work), flush=True)
    print('ENV_CHECK_LOG=' + str(log), flush=True)

    def record(name, ok, detail):
        checks.append(dict(name=name, passed=ok, detail=detail))
        if not ok: errors.append(name)
        print(('OK   ' if ok else 'FAIL ') + name + ': ' + detail, flush=True)

    def run(name, argv, pattern=None, cwd=log, timeout=60):
        resolved = shutil.which(str(argv[0]))
        actual = [resolved or str(argv[0]), *map(str, argv[1:])]
        output, rc = '', 2
        print('CHECK ' + name + ' -> ' + actual[0], flush=True)
        path = log / (name + '.log')
        try:
            if resolved is None:
                raise FileNotFoundError('Executable not found or not executable: ' + actual[0])
            with path.open('w', encoding='utf8') as stream:
                p = subprocess.Popen(actual, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                     start_new_session=True)
                try:
                    rc = p.wait(timeout=timeout)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
                    stream.write('\nCHECK_TIMEOUT_OR_INTERRUPTED\n')
                    rc = 124
            output = path.read_text(encoding='utf8', errors='replace')
        except OSError as exc:
            output = str(exc)
            path.write_text(output, encoding='utf8')
        ok = rc == 0 and (pattern is None or re.search(pattern, output) is not None)
        detail = next((line for line in output.splitlines() if line.strip()), '(no stdout)')[:220]
        record(name, ok, detail + (' [version mismatch]' if rc == 0 and not ok else ''))
        checks[-1].update(argv=actual, cwd=str(cwd), exit_code=rc, log=str(path), expected_pattern=pattern)
        return ok, output

    record('linux-source-location', not str(ROOT).startswith('/mnt/'), str(ROOT))
    for rel in ['vdot-restored.json', 'XiangShan/build.sc', 'XiangShan/.mill-version',
                'NEMU/.config', 'nexus-am/Makefile']:
        record('prepared-' + rel.replace('/', '-'), (work / rel).is_file(), str(work / rel))
    if not (work / 'vdot-restored.json').is_file():
        print('ACTION: first run python3 tools/prepare_sources.py (new work/build only).', flush=True)
    config = (work / 'NEMU/.config').read_text() if (work / 'NEMU/.config').is_file() else ''
    def config_tool(key, default):
        match = re.search(r'^' + key + r'="([^"]+)"$', config, re.M)
        return match[1] if match else default

    cc = choose('VDOT_CC', ['clang-19', 'clang'])
    cxx = choose('VDOT_CXX', ['clang++-19', 'clang++'])
    cross = choose('VDOT_RISCV_CC', ['riscv64-linux-gnu-gcc-12', 'riscv64-linux-gnu-gcc'])
    nemu_cc, nemu_cxx = config_tool('CONFIG_CC', 'clang'), config_tool('CONFIG_CXX', 'clang++')
    java = str(Path(os.environ['JAVA_HOME']) / 'bin/java') if os.environ.get('JAVA_HOME') else 'java'
    for name, argv, pattern in [
        ('java-path', ['java', '-version'], r'version "21\.'),
        ('java-for-mill', [java, '-version'], r'version "21\.'),
        ('javac', ['javac', '-version'], r'javac 21\.'),
        ('verilator', ['verilator', '--version'], r'Verilator 5\.052\b'),
        ('emu-cc', [cc, '--version'], r'clang version 19\.'),
        ('emu-cxx', [cxx, '--version'], r'clang version 19\.'),
        ('nemu-cc', [nemu_cc, '--version'], r'clang version 19\.'),
        ('nemu-cxx', [nemu_cxx, '--version'], r'clang version 19\.'),
        ('make', ['make', '--version'], r'GNU Make'),
        ('gnu-time', ['time', '--version'], r'GNU [Tt]ime'),
        ('git', ['git', '--version'], r'git version'),
        ('python', [sys.executable, '--version'], None),
        ('perl', ['perl', '-v'], None), ('flex', ['flex', '--version'], None),
        ('bison', ['bison', '--version'], None),
    ]:
        run(name, argv, pattern)
    # A generic Mill launcher must see the project's version pin, not a temp directory.
    if (work / 'XiangShan/.mill-version').is_file():
        run('mill', ['mill', '--version'], r'Mill Build Tool version 0\.12\.3\b', cwd=work / 'XiangShan')
    else:
        record('mill', False, 'Missing prepared .mill-version; not launching an unpinned Mill.')
    ok, version = run('riscv-gcc', [cross, '-dumpfullversion'])
    if ok and not version.strip().startswith('12.'):
        warnings.append('RISC-V GCC differs from historical GCC 12; new images may have different addresses/cycles.')
    for tool in ['ld', 'objcopy', 'objdump', 'ar']:
        run('riscv-' + tool, ['riscv64-linux-gnu-' + tool, '--version'])
    if 'CONFIG_LIBCHECKPOINT_ALPHA_RESTORER=y' in config:
        try:
            prefix, selected = prepare_checkpoint_toolchain()
            record('checkpoint-selection', True, json.dumps(selected))
            for tool in ['gcc', 'ld', 'objcopy', 'objdump']:
                run('checkpoint-' + tool, [prefix + tool, '--version'])
        except (OSError, ValueError) as error:
            record('checkpoint-selection', False, str(error))

    (log / 'Probe.java').write_text('class Probe { public static void main(String[] a) { System.out.println("JDK_OK"); } }\n')
    if run('jdk-compile', ['javac', 'Probe.java'])[0]:
        run('jdk-run', [java, '-cp', str(log), 'Probe'], r'JDK_OK')
    (log / 'probe.c').write_text('#include <stdint.h>\n#include <zlib.h>\nint probe(void){return zlibVersion()!=0;}\n')
    run('nemu-c-compile', [nemu_cc, '-fPIC', '-c', 'probe.c', '-o', 'probe-c.o'])
    run('emu-c-compile', [cc, '-fPIC', '-c', 'probe.c', '-o', 'probe-emu-c.o'])
    (log / 'probe.cpp').write_text('#include <zlib.h>\n#include <dlfcn.h>\n#include <iostream>\nint main(){std::cout<<zlibVersion();return dlopen(nullptr,RTLD_LAZY)?0:1;}\n')
    if run('host-link', [cxx, 'probe.cpp', '-std=c++17', '-lz', '-ldl', '-pthread', '-o', 'probe'])[0]:
        run('host-run', [str(log / 'probe')])
    run('nemu-shared-link', [nemu_cxx, 'probe.cpp', '-std=c++17', '-shared', '-fPIC',
                           '-static-libstdc++', '-Wl,--no-undefined', '-lz', '-ldl', '-o', 'probe.so'])
    (log / 'sqlite.cpp').write_text('#include <sqlite3.h>\nint main(){sqlite3 *db=nullptr;int rc=sqlite3_open(":memory:",&db);if(db)sqlite3_close(db);return rc;}\n')
    if run('sqlite-link', [cxx, 'sqlite.cpp', '-std=c++17', '-lsqlite3', '-o', 'sqlite-probe'])[0]:
        run('sqlite-run', [str(log / 'sqlite-probe')])
    if 'CONFIG_ZSTD_COMPRESS=y' in config:
        (log / 'zstd.c').write_text('#include <zstd.h>\nint main(){return ZSTD_versionNumber()==0;}\n')
        run('zstd-link', [nemu_cc, 'zstd.c', '-lzstd', '-o', 'zstd-probe'])
    (log / 'vector.S').write_text('.text\n.globl _start\n_start:\n vsetivli zero, 4, e32, m1, ta, ma\n vadd.vv v3, v1, v2\n ret\n')
    if run('rvv-assemble', [cross, '-march=rv64gcv', '-mabi=lp64d', '-c', 'vector.S', '-o', 'vector.o'])[0]:
        if run('rvv-link', ['riscv64-linux-gnu-ld', '-e', '_start', '-Ttext=0x80000000', 'vector.o', '-o', 'vector.elf'])[0]:
            run('rvv-binary', ['riscv64-linux-gnu-objcopy', '-O', 'binary', 'vector.elf', 'vector.bin'])
    # Tiny traced model exercises Verilator -> C++ -> Make -> executable, not XiangShan RTL.
    (log / 'Probe.sv').write_text('module Probe(input logic a, output logic b); assign b = ~a; endmodule\n')
    (log / 'sim.cpp').write_text('#include "VProbe.h"\nint main(){VProbe p;p.a=0;p.eval();return p.b==1?0:1;}\n')
    if run('verilator-build', ['verilator', '--cc', '--trace', '--exe', '--build', '-j', '2',
                              '--top-module', 'Probe', '--Mdir', 'obj_dir',
                              '-MAKEFLAGS', 'CXX=' + cxx, '-MAKEFLAGS', 'LINK=' + cxx,
                              'Probe.sv', 'sim.cpp'])[0]:
        run('verilator-run', [str(log / 'obj_dir/VProbe')])
    free = shutil.disk_usage(ROOT).free
    record('disk-space', free >= 20 * 2**30, '%.1f GiB free; preflight threshold 20 GiB' % (free / 2**30))
    resources = {'free_disk_bytes': free, 'cpu_affinity_count': len(os.sched_getaffinity(0))}
    for name in ['/proc/meminfo', '/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/cpu.max']:
        p = Path(name)
        if p.is_file(): resources[name] = p.read_text()
    for variable in ['VDOT_JOBS', 'VDOT_APP_JOBS']:
        value = os.environ.get(variable, '4' if variable == 'VDOT_JOBS' else '2')
        record(variable, value.isdigit() and int(value) > 0, value)
    warnings.append('Scala/Maven dependency completeness is checked by the subsequent build; Mill --version alone does not check it.')
    result = dict(repository=str(ROOT), work=str(work), argv=sys.argv, cwd=str(Path.cwd()),
                  platform=platform.platform(), checks=checks, errors=errors, warnings=warnings,
                  resources=resources, exit_code=2 if errors else 0,
                  scope='Prepared source sentinels, selected tool versions, Java/C/C++/RVV and traced Verilator probes; no full-core build or simulation.')
    (log / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    (log / 'exit-code.txt').write_text(str(result['exit_code']) + '\n')
    for warning in warnings: print('NOTE: ' + warning)
    print('ENV_CHECK_LOG=' + str(log))
    print('ENV_CHECK=' + ('FAIL' if errors else 'PASS'))
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
