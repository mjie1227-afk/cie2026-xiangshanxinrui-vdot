"""Prepare a Linux build tree from the source files already included in this repository."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, os, shutil, sys
ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('destination', nargs='?', type=Path, default=ROOT/'work/build')
    ap.add_argument('--plan', action='store_true', help='Print paths and versions; do not copy or build')
    args = ap.parse_args()
    destination = args.destination.expanduser().resolve()
    metadata = json.loads((ROOT/'configs/source-tree.json').read_text(encoding='utf8'))
    plan = {'repository': str(ROOT), 'destination': str(destination),
            'source_files': len(metadata['entries']), 'network_required_for_source_preparation': False,
            'patches_already_applied': True, 'repositories': metadata['repositories']}
    if args.plan:
        print(json.dumps(plan, ensure_ascii=False, indent=2)); return 0
    if sys.platform != 'linux':
        ap.error('Run in Ubuntu WSL/Linux from a repository copy on the Linux filesystem.')
    if destination.exists():
        ap.error('Destination already exists; keep it and choose a new directory: '+str(destination))
    if destination.is_relative_to('/mnt'):
        ap.error('Copy this repository to ~/cie2026-xiangshanxinrui-vdot first, then run from its root.')
    if not destination.is_relative_to(ROOT/'work'):
        ap.error('Keep the build under this repository: work/build or work/build-02.')
    for item in metadata['entries']:
        rel = PurePosixPath(item['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Unsafe source path: '+item['path'])
        source = (ROOT/item['stored']).resolve()
        if not source.is_relative_to(ROOT/'src') or digest(source) != item['sha256']:
            raise ValueError('Source checksum mismatch: '+item['stored'])
        if item['type'] == 'symlink':
            target = (destination/rel).parent/item['target']
            if not target.resolve().is_relative_to(destination):
                raise ValueError('Symlink leaves build directory: '+item['path'])
    destination.mkdir(parents=True)
    for item in metadata['entries']:
        target = destination/item['path']; target.parent.mkdir(parents=True, exist_ok=True)
        if item['type'] == 'symlink':
            target.symlink_to(item['target'])
        else:
            shutil.copyfile(ROOT/item['stored'], target)
            target.chmod(int(item['mode'], 8))
    shutil.copyfile(ROOT/'configs/nemu.config', destination/'NEMU/.config')
    apps = json.loads((ROOT/'configs/apps.json').read_text())['applications']
    for name in apps:
        target = destination/'nexus-am/apps'/name
        if target.exists():
            raise ValueError('Application name already exists: '+name)
        shutil.copytree(ROOT/'apps'/name, target)
    shutil.copyfile(ROOT/'configs/boot-flash.bin', destination/'boot-flash.bin')
    record = {**plan, 'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.version,
              'source_tree_sha256': digest(ROOT/'configs/source-tree.json'),
              'applications': apps, 'status': 'sources prepared; not built or simulated'}
    (destination/'vdot-restored.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
    print('SOURCE_PREPARE_OK', destination)
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr); raise SystemExit(1)
