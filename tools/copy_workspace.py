"""Copy this repository's delivery files into a new Linux-local recording/build workspace."""
from pathlib import Path
import argparse,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('destination',nargs='?',type=Path,default=Path.home()/'cie2026-xiangshanxinrui-vdot')
    args=ap.parse_args();dest=args.destination.expanduser().resolve()
    if sys.platform!='linux':ap.error('Run this command through Ubuntu WSL or Linux.')
    if dest.exists():ap.error('Destination exists; use that copy or choose a new name: '+str(dest))
    if dest.is_relative_to('/mnt') or dest.is_relative_to(ROOT):ap.error('Choose a new Linux filesystem directory outside the source copy.')
    rows=(ROOT/'MANIFEST.sha256').read_text(encoding='utf8').splitlines()
    paths=[line.split('  ',1)[1] for line in rows]+['MANIFEST.sha256']
    for rel in paths:
        source=(ROOT/rel).resolve()
        target=(dest/rel).resolve()
        if not source.is_relative_to(ROOT) or not target.is_relative_to(dest) or not source.is_file():ap.error('Invalid manifest entry: '+rel)
    dest.mkdir(parents=True)
    for rel in paths:
        target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,target)
    print('WORKSPACE_COPY_OK',dest)
    print('Next: cd "'+str(dest)+'" && python3 tools/verify_bundle.py')
    return 0
if __name__=='__main__':raise SystemExit(main())
