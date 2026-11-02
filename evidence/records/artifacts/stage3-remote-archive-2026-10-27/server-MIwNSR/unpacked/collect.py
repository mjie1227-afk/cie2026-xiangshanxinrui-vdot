"""Archive saved stage-3 logs and samples. Never execute source-side programs."""
import datetime
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
import time
from pathlib import Path

PRIMARY = [
    'vdot-rvv-equiv-8nvimb', 'vdot-timing-retry-5vHUp8',
    'vdot-chain-KiI3xX', 'vdot-tput-uLgHm6', 'vdot-e2e-bijzGZ']
SUPPORT = {
    'vdot-timing-pilot-IgNim5': ['architecture.log', 'build.log', 'matrix.json', 'runtime-identities.json'],
    'vdot-build-80mKCD': ['nemu-config.log', 'nemu-build.log', 'emu-build.log', 'vdot-smoke.log'],
    'vdot-matrix-OMcrpf': ['vdot-exceptions.log', 'vdot-exceptions.exit', 'vdot-overlap.log'],
    'vdot-mtval-build-xYGYlZ': ['emu-build.log', 'vdot-exceptions.log', 'vdot-exceptions.exit', 'vdot-overlap.log'],
    'vdot-pipeline-JuGUz6': ['vdot-deps.log', 'vdot-mixed.log', 'vdot-cancel-csr.log']}
COMMON = ['architecture.log', 'architecture.argv.json', 'result.json', 'environment.json']
NORMAL = ['build.log', 'build.argv.json', 'console.log', 'exit-status.txt', 'matrix.json',
          'runtime-identities.json', 'identity-before.json', 'identity-after.json', 'kernel-identities.json']
RETRY = ['expected.sha256', 'identity-before.txt', 'identity-after.txt', 'run-result.txt',
         'script-result.txt', 'start.txt', 'end.txt', 'helpers.sha256']
SAMPLES = ['samples.json', 'samples.csv', 'raw-statistics.json']
TEXT = {'.log', '.txt', '.json', '.csv', '.tsv', '.sha256', '.argv', '.env', '.exit',
        '.nm', '.disasm', '.patch', '.diff', '.config', '.md', '.yaml', '.yml', '.py', '.sh'}


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()


def stamp(p):
    s = p.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def save(p, value):
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def collect(work, out):
    started = time.monotonic()
    work, out = work.resolve(strict=True), out.resolve(strict=True)
    required = {n: COMMON + (RETRY if n == PRIMARY[1] else NORMAL) +
                ([] if n == PRIMARY[0] else SAMPLES) for n in PRIMARY}
    required.update(SUPPORT)
    selected, excluded, missing = [], [], []
    for name, required_names in required.items():
        root = work / 'evidence' / name
        if not root.is_dir() or root.is_symlink():
            missing.append(str(root))
            continue
        if root.resolve() != root or root == out or root in out.parents:
            raise RuntimeError('Unexpected source/output location: ' + str(root))
        for filename in required_names:
            p = root / filename
            if not p.is_file() or p.is_symlink() or p.stat().st_size == 0:
                missing.append(str(p))
        for directory, dirs, files in os.walk(root, followlinks=False):
            for item in dirs[:]:
                p = Path(directory) / item
                if p.is_symlink():
                    raise RuntimeError('Source symlink directory: ' + str(p))
            for filename in sorted(files):
                p = Path(directory) / filename
                if not stat.S_ISREG(p.lstat().st_mode):
                    raise RuntimeError('Non-regular source file: ' + str(p))
                rel = p.relative_to(work).as_posix()
                if p.suffix.lower() in TEXT or '.log' in p.suffixes or filename in ('stdout', 'stderr'):
                    selected.append(p)
                else:
                    excluded.append({'path': rel, 'bytes': p.stat().st_size, 'reason': 'outside declared log/metadata scope'})
    save(out / 'preflight.json', {'required_runs': list(required), 'missing': missing, 'excluded': excluded})
    if missing:
        raise RuntimeError('Missing required evidence; see preflight.json: ' + '; '.join(missing))
    total = sum(p.stat().st_size for p in selected)
    if shutil.disk_usage(out).free < total + max(64 * 1024**2, total // 10):
        raise RuntimeError('Insufficient space for archive; sources retained')
    entries, versions = [], {}
    for p in sorted(selected):
        before = stamp(p)
        with p.open('rb') as f:
            sha = digest(f)
        if stamp(p) != before:
            raise RuntimeError('Source changed while hashing: ' + str(p))
        versions[p] = before
        entries.append({'path': p.relative_to(work).as_posix(), 'bytes': before[2], 'sha256': sha})
    print('SELECTED_FILES=%d SOURCE_BYTES=%d EXCLUDED_FILES=%d' % (len(entries), total, len(excluded)), flush=True)
    manifest = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'source_root': str(work), 'scope': '10 named runs: complete selected logs and metadata; no waveforms or executable binaries',
                'new_simulation': False, 'new_build': False, 'files': entries, 'excluded': excluded,
                'identity_note': 'Saved runtime identity files are copied; current emu/NEMU/images are not rehashed.'}
    save(out / 'manifest.json', manifest)
    with (out / 'SHA256SUMS').open('x', encoding='utf-8') as f:
        for item in entries:
            f.write(item['sha256'] + '  ' + item['path'] + '\n')
    archive = out / 'stage3-logs.tar.gz'
    metadata = ['manifest.json', 'SHA256SUMS', 'preflight.json']
    if (out / 'collect.py').is_file():
        metadata.append('collect.py')
    with tarfile.open(archive, 'x:gz', compresslevel=6) as tf:
        last_run = None
        for item in entries:
            p = work / item['path']
            run = p.parts[len(work.parts) + 1]
            if run != last_run:
                print('PACKING=' + run, flush=True)
                last_run = run
            if stamp(p) != versions[p]:
                raise RuntimeError('Source changed before archive: ' + str(p))
            tf.add(p, arcname=item['path'], recursive=False)
        for name in metadata:
            tf.add(out / name, arcname=name, recursive=False)
    for p, previous in versions.items():
        if stamp(p) != previous:
            raise RuntimeError('Source changed during archive: ' + str(p))
    print('VERIFYING_ARCHIVE_MEMBERS', flush=True)
    expected = {item['path']: item['sha256'] for item in entries}
    for name in metadata:
        with (out / name).open('rb') as f:
            expected[name] = digest(f)
    seen = set()
    with tarfile.open(archive, 'r:gz') as tf:
        for member in tf:
            if not member.isfile() or member.name not in expected or member.name in seen:
                raise RuntimeError('Unexpected archive member: ' + member.name)
            with tf.extractfile(member) as f:
                if digest(f) != expected[member.name]:
                    raise RuntimeError('Archive hash mismatch: ' + member.name)
            seen.add(member.name)
    if seen != set(expected):
        raise RuntimeError('Archive member list incomplete')
    with archive.open('rb') as f:
        archive_sha = digest(f)
    (out / 'stage3-logs.tar.gz.sha256').write_text(archive_sha + '  stage3-logs.tar.gz\n', encoding='ascii')
    result = {'status': 'archive-verified-for-declared-scope', 'exit': 0, 'source_runs': len(required),
              'files': len(entries), 'source_bytes': total, 'excluded_files': len(excluded),
              'archive': str(archive), 'archive_bytes': archive.stat().st_size, 'sha256': archive_sha,
              'wall_seconds': round(time.monotonic() - started, 3), 'argv': sys.argv,
              'new_simulation': False, 'new_build': False}
    save(out / 'collection-result.json', result)
    print('ARCHIVE=' + str(archive))
    print('ARCHIVE_BYTES=' + str(archive.stat().st_size))
    print('ARCHIVE_SHA256=' + archive_sha)
    print('STAGE3_ARCHIVE_READY')


if __name__ == '__main__':
    try:
        collect(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as error:
        print('STAGE3_ARCHIVE_ERROR=' + str(error), file=sys.stderr)
        sys.exit(2)

