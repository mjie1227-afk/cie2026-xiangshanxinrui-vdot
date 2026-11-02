"""Archive missing stage-2 evidence; skip identical local bytes. Never execute source-side programs."""
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

PRIMARY = []
SUPPORT = {'vdot-wave-window-Cpa0HX': ['result.json', 'capture.log', 'cancel-window.vcd'], 'vdot-window-events-UbYWTP': ['result.json', 'events.jsonl', 'targets.json'], 'vdot-window-supplement-fgpWCe': ['result.json', 'supplement.json', 'source-route-proof.json', 'identity-rejections.json'], 'vdot-csr-commit-window-aReAEz': ['result.json', 'csr-observations.json', 'mismatches.json'], 'vdot-mixed-wave-FNmKGI': ['result.json', 'capture.log', 'mixed-window.vcd'], 'vdot-mixed-resources-9k3waS': ['result.json', 'events.json', 'resource-events.json', 'target-summary.json'], 'vdot-mixed-route-audit-ApJqcC': ['audit-result.json', 'resource-coverage.json', 'target-routes.json'], 'vdot-port-candidate-eDAWKv': ['result.json', 'architecture.log', 'prefix.log', 'runtime-identities.json'], 'vdot-port-wave-EfQru1': ['result.json', 'capture.log', 'argv.json'], 'vdot-port-events-FfVozt': ['result.json', 'events.json', 'request-events.json', 'resource-coverage.json', 'pair-review.json']}
COMMON = NORMAL = RETRY = SAMPLES = []
TEXT = {'.log','.txt','.json','.jsonl','.csv','.tsv','.sha256','.argv','.env','.exit','.nm','.disasm','.patch','.diff','.config','.md','.yaml','.yml','.py','.sh'}
WAVES = {'evidence/vdot-wave-window-Cpa0HX/cancel-window.vcd': 457224402, 'evidence/vdot-mixed-wave-FNmKGI/mixed-window.vcd': 477548918}
KNOWN = {'evidence/vdot-wave-window-Cpa0HX/review.json': 'a09ab85585760057112dd728290572312413b25868fcdbc2044caebb5e742c44', 'evidence/vdot-wave-window-Cpa0HX/user-result-excerpt.txt': 'a32fa7d05be129bec434ed0c59b2a621b14a1f3f9b6b448fa04d6be889866413', 'evidence/vdot-window-events-UbYWTP/review.json': 'f7d2e31d95b5629d738c12dd0144b1ec6757793aa780edaf5dcda63c39532c20', 'evidence/vdot-window-events-UbYWTP/targets.json': '1cb2e2af6b44f5823b34a06a00d9ed1742285e1714f683da2a900f0d8faa970c', 'evidence/vdot-window-events-UbYWTP/user-output.txt': '7df359a26e4b6699a8bff413930b9cad56e1d3c0282c1ab34764d403f659ec7a', 'evidence/vdot-window-supplement-fgpWCe/focus-details.json': '5b9ff498b60a546ec8f068efb1b2c910df02f4da7b90cde7070a53b1acd997af', 'evidence/vdot-window-supplement-fgpWCe/review.json': '14787d72dfa1bc78b220d9768fb9b1d14722aba386b95b6b2a550e7a027d414e', 'evidence/vdot-window-supplement-fgpWCe/user-output.txt': 'e52966b2093f71b4990b2225dd9e51e949e8ecacbee0dc5ca6c0ce54f12e6b61', 'evidence/vdot-csr-commit-window-aReAEz/review.json': 'c265c6608ad8e3a0941838e9087f3fd4e6e0f9f042493183209d2d255d673273', 'evidence/vdot-csr-commit-window-aReAEz/user-output.txt': 'f689104b866c0082bf4dc6701abfa0e58e0bae325d1badabef135d6ff563c264', 'evidence/vdot-mixed-wave-FNmKGI/review.json': '7721dfe56043a511b8aba398b3879523a9e4b5c3bb13563d02363192bf8e14b7', 'evidence/vdot-mixed-wave-FNmKGI/user-runtime-excerpt.txt': '34d92e2e6a5b42bce0c71944199a471005b5476bbbb8eff6c860fc74a52ec79c', 'evidence/vdot-mixed-resources-9k3waS/resource-schema.json': 'c54c69482bce59237a27bc6fed6f12376028cc258b8cca6e47ee6e3443b3fab6', 'evidence/vdot-mixed-resources-9k3waS/review.json': '9f9169dccd75501954edbe3dc1808939c3bdd119c084f56c675836fd903b2876', 'evidence/vdot-mixed-resources-9k3waS/runtime-summary.json': 'de48187ffe7b75d5fe4269994ad085671ee5e8956b84b12821092dc1d2241e9d', 'evidence/vdot-mixed-resources-9k3waS/targets.json': 'd40b95d1df172e232b24c1fec25afa5427f57c47c2b6bdb4f312b60deea92243', 'evidence/vdot-mixed-resources-9k3waS/user-output.txt': '194b9fc1ce7de46129a2cd357353b50cacf2551338e774fa560b00a28fff63e2', 'evidence/vdot-mixed-route-audit-ApJqcC/audit-summary.json': '87b3adf19ed6d8d5edb78be9edf44dc0a28cd8653bc1fa87cec535d762e5f76c', 'evidence/vdot-mixed-route-audit-ApJqcC/resource-coverage.json': 'dde18a240660e62b55763f55eda1f547e125a3f78eebb5093af1eb65f5249e16', 'evidence/vdot-mixed-route-audit-ApJqcC/review.json': '9e30e4885ba1935cf27b5517026cf20ea98248f9f750397db5de5bdbbc287a81', 'evidence/vdot-mixed-route-audit-ApJqcC/target-requests.json': 'f933222285e2744c5f8516c2214eaeb0989bb6016d9cd6822a2b76980767096d', 'evidence/vdot-mixed-route-audit-ApJqcC/target-routes.json': '1498d9ca8a5a2c74131a43363bd7a11c8248c329d8bdf077068fee074072027a', 'evidence/vdot-mixed-route-audit-ApJqcC/user-output.txt': '3e162254daaed376297c0566a27cd7ed43dca17bc163e8fbb01d7a6e8f5ebc14', 'evidence/vdot-port-candidate-eDAWKv/review.json': '3e9499718bc9c80bbb9b11e2178e37a3062b62dd992950098095c134a73f5b27', 'evidence/vdot-port-candidate-eDAWKv/user-output.txt': 'f91cc4a5930485d84fbf22bd485a77fd42fb64c1d7b053eac4e33893bd4292b1', 'evidence/vdot-port-wave-EfQru1/identities.json': 'e588b5ef17912985144ac587bc3ab3ed842f8bd3079851491db3dda7b32d5c4b', 'evidence/vdot-port-wave-EfQru1/review.json': '8ac023b2237f88494dca64519dd258d7eead2629d2e9581e016c0728f9586c6e', 'evidence/vdot-port-wave-EfQru1/user-output.txt': '2ef068b9fd155d9ddbf2f6aedc8679140c2bab9ec29540fa7599329539c97180', 'evidence/vdot-port-events-FfVozt/coverage.json': '28a876c313bfcd0bab8f1d66400993ad2b13831497a7c3366f491af2bfa79571', 'evidence/vdot-port-events-FfVozt/document-check.json': 'ff68f05b418616204501727ffdb2e3652f0ea0dbc0baf457768938f5ef23f6d0', 'evidence/vdot-port-events-FfVozt/pairs.json': '20de84e7c8e092b009002172233b789fc1fa39f85cdc8c0a129a43f339d485b4', 'evidence/vdot-port-events-FfVozt/requests.json': 'a4834d3ba05e72f450af2ed63ca8d300071de6e158ee5c8d3545e96fb0e087cd', 'evidence/vdot-port-events-FfVozt/review.json': 'd2d4171431606f84d36cff420e6a37931e80a33c130dc316bf7c1931f5738790', 'evidence/vdot-port-events-FfVozt/sampling-domains.json': '8b253c86b02f7fc9fcb9ca769d923b9d28e977f35ce6007256e442ce74d81b41', 'evidence/vdot-port-events-FfVozt/summary.json': '4f9569cd5e6a0eb987e3f4a254d249d997bae2ed5467e0fbc241e733ae27bb4f', 'evidence/vdot-port-events-FfVozt/targets.json': '77859763ca9d3a0d93ef88a085dbf7d860c5b7416126aea3fd1dd283aea3f964', 'evidence/vdot-port-events-FfVozt/user-output.txt': '7dd5f6b58488b2e01f286528bb3f9965c3cfa88b695c6980a55e86a4d1bf6927'}


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
                if p.suffix.lower() in TEXT or '.log' in p.suffixes or filename in ('stdout', 'stderr') or rel in WAVES:
                    if rel in WAVES and p.stat().st_size != WAVES[rel]:
                        raise RuntimeError('Recorded VCD size differs: ' + rel)
                    if rel in KNOWN:
                        before = stamp(p)
                        with p.open('rb') as f:
                            same = digest(f) == KNOWN[rel]
                        if stamp(p) != before:
                            raise RuntimeError('Source changed while deduplicating: ' + rel)
                        if same:
                            excluded.append({'path': rel, 'bytes': before[2], 'reason': 'identical bytes already archived locally', 'sha256': KNOWN[rel]})
                            continue
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
                'source_root': str(work), 'scope': '10 missing stage-2 evidence runs; selected logs/JSONL plus exactly two missing VCDs; identical local bytes skipped',
                'new_simulation': False, 'new_build': False, 'files': entries, 'excluded': excluded,
                'identity_note': 'Saved runtime identity files are copied; current emu/NEMU/images are not rehashed.'}
    save(out / 'manifest.json', manifest)
    with (out / 'SHA256SUMS').open('x', encoding='utf-8') as f:
        for item in entries:
            f.write(item['sha256'] + '  ' + item['path'] + '\n')
    archive = out / 'stage2-missing-evidence.tar.gz'
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
    (out / 'stage2-missing-evidence.tar.gz.sha256').write_text(archive_sha + '  stage2-missing-evidence.tar.gz\n', encoding='ascii')
    result = {'status': 'archive-verified-for-declared-scope', 'exit': 0, 'source_runs': len(required),
              'files': len(entries), 'source_bytes': total, 'excluded_files': len(excluded),
              'archive': str(archive), 'archive_bytes': archive.stat().st_size, 'sha256': archive_sha,
              'wall_seconds': round(time.monotonic() - started, 3), 'argv': sys.argv,
              'new_simulation': False, 'new_build': False}
    save(out / 'collection-result.json', result)
    print('ARCHIVE=' + str(archive))
    print('ARCHIVE_BYTES=' + str(archive.stat().st_size))
    print('ARCHIVE_SHA256=' + archive_sha)
    print('STAGE2_MISSING_ARCHIVE_READY')


if __name__ == '__main__':
    try:
        collect(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as error:
        print('STAGE2_MISSING_ARCHIVE_ERROR=' + str(error), file=sys.stderr)
        sys.exit(2)

