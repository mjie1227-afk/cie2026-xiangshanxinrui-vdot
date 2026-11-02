"""Restore pinned upstream code plus VDot patches into a NEW Linux directory."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('destination',type=Path,help='New directory on the Linux filesystem')
 ap.add_argument('--plan',action='store_true',help='Print revisions only; no network or writes')
 a=ap.parse_args();dest=a.destination.expanduser().resolve()
 lock=json.loads((ROOT/'configs/upstream-lock.json').read_text())
 if a.plan:
  print(json.dumps({'destination':str(dest),'repositories':lock},indent=2));return 0
 if sys.platform!='linux':ap.error('Run source restoration in Linux/Ubuntu WSL.')
 if dest.exists():ap.error(f'Destination already exists; choose a new directory: {dest}')
 if dest.is_relative_to('/mnt'):ap.error('Choose a Linux filesystem path such as ~/cie-vdot-work.')
 dest.mkdir(parents=True);log=dest/'restore.log'
 env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0')
 def run(args,cwd=None):
  with log.open('a',encoding='utf8') as f:
   f.write(json.dumps({'argv':list(map(str,args)),'cwd':str(cwd or dest)})+'\n');f.flush()
   r=subprocess.run(list(map(str,args)),cwd=cwd or dest,env=env,stdout=f,stderr=subprocess.STDOUT)
   f.write(f'EXIT_CODE={r.returncode}\n')
  if r.returncode:raise RuntimeError(f'Command failed; inspect {log}')
 def clone(url,head,path):
  if path.exists() and any(path.iterdir()):raise RuntimeError(f'Refusing nonempty checkout: {path}')
  run(['git','clone','--filter=blob:none','--no-checkout',url,path])
  run(['git','checkout','--detach',head],path)
 for name,info in lock.items():
  path=dest/name;print('Restoring',name,info['commit'],flush=True)
  clone(info['url'],info['commit'],path)
  for rel,dep in sorted(info.get('dependencies',{}).items(),key=lambda x:len(Path(x[0]).parts)):
   clone(dep['url'],dep['commit'],path/rel)
  if name in ['XiangShan','NEMU']:
   patch=ROOT/'patches'/('XiangShan-full.patch' if name=='XiangShan' else 'NEMU.patch')
   run(['git','apply','--check',patch],path);run(['git','apply',patch],path)
   expected=json.loads((ROOT/'configs/source-snapshots.json').read_text())[name]
   for rel,digest in expected.items():
    if hashlib.sha256((path/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Patched source differs: '+rel)
 shutil.copy2(ROOT/'configs/nemu.config',dest/'NEMU/.config')
 for app in json.loads((ROOT/'configs/apps.json').read_text())['applications']:
  target=dest/'nexus-am/apps'/app
  if target.exists():raise RuntimeError(f'Application directory already exists: {target}')
  shutil.copytree(ROOT/'apps'/app,target)
 shutil.copy2(ROOT/'configs/boot-flash.bin',dest/'boot-flash.bin')
 (dest/'vdot-restored.json').write_text(json.dumps({'repository':str(ROOT),'upstream':lock,'status':'sources restored; not compiled or simulated'},indent=2))
 print('SOURCE_RESTORE_OK',dest);return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except (OSError,RuntimeError) as e:print(str(e),file=sys.stderr);raise SystemExit(1)
