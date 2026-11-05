"""Resolve GCC/binutils once for both environment checks and NEMU builds."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def executable(candidates):
    for item in candidates:
        if item and shutil.which(str(item)):
            return str(Path(shutil.which(str(item))).absolute())
    raise FileNotFoundError('No executable found: ' + ', '.join(map(str, candidates)))


def prepare(root=ROOT):
    requested = os.environ.get('CPT_CROSS_COMPILE')
    compiler = os.environ.get('VDOT_RISCV_CC')
    if requested:
        gcc = executable([requested + 'gcc', requested + 'gcc-12'])
        stem = requested
    else:
        gcc = executable([compiler] if compiler else ['riscv64-linux-gnu-gcc-12', 'riscv64-linux-gnu-gcc'])
        match = re.match(r'(.+-)gcc(?:-\d+)?$', Path(gcc).name)
        if not match:
            raise ValueError('Cannot infer binutils prefix; set CPT_CROSS_COMPILE explicitly: ' + gcc)
        stem = str(Path(gcc).parent / match[1])
    selected = {'gcc': gcc}
    for tool in ['ld', 'objcopy', 'objdump']:
        # Preserve the selected toolchain directory rather than mixing arbitrary prefixes.
        selected[tool] = executable([stem + tool])
    identity = hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()[:16]
    folder = root / 'work/toolchains' / identity / 'bin'
    folder.mkdir(parents=True, exist_ok=True)
    for tool, target in selected.items():
        link = folder / ('riscv64-linux-gnu-' + tool)
        if link.is_symlink() or link.exists():
            if not link.is_symlink() or link.resolve() != Path(target).resolve():
                raise ValueError('Existing tool entry differs; preserved: ' + str(link))
        else:
            link.symlink_to(target)
    (folder.parent / 'tools.json').write_text(json.dumps(selected, indent=2) + '\n')
    return str(folder / 'riscv64-linux-gnu-'), selected


if __name__ == '__main__':
    try:
        print(prepare()[0])
    except (OSError, ValueError) as error:
        print('CHECKPOINT_TOOLCHAIN_ERROR: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
