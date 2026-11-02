"""Create a fresh XiangShan-only checkout; never modify original emu or NEMU."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
payload=Path(__file__).resolve().parent
manifest=json.loads((payload/'manifest.json').read_text())
work=Path('/root/private_data/mj/xiangshan')
src=work/'vdot-dev-20261024/XiangShan'
dest=work/'vdot-mtval-fix-20261024/XiangShan'
log=Path(sys.argv[1]); records=[]
def run(argv):
    p=subprocess.run(list(map(str,argv)),capture_output=True,text=True,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_TERMINAL_PROMPT='0'))
    records.append({'argv':list(map(str,argv)),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    (log/'apply-records.json').write_text(json.dumps(records,indent=2)+'\n')
    if p.returncode: raise RuntimeError(p.stderr)
    return p.stdout.strip()
for rel,digest in manifest['files'].items():
    assert hashlib.sha256((payload/rel).read_bytes()).hexdigest()==digest,rel
assert not dest.parent.exists(),'Destination already exists: stop and inspect, do not delete it'
run(['git','-C',src,'rev-parse','--show-toplevel'])
run(['git','-C',src,'branch','--show-current'])
assert run(['git','-C',src,'rev-parse','HEAD'])==manifest['base_head']
assert not run(['git','-C',src,'diff','--cached','--name-only']),'Unexpected staged changes'
changed=set(run(['git','-C',src,'diff','--name-only']).splitlines())
changed.update(run(['git','-C',src,'ls-files','--others','--exclude-standard']).splitlines())
assert changed==set(manifest['previous_sources']),f'Unexpected original source changes: {changed.symmetric_difference(manifest["previous_sources"])}'
for rel,digest in manifest['previous_sources'].items():
    assert hashlib.sha256((src/rel).read_bytes()).hexdigest()==digest,rel
repos=[(Path('.'),manifest['base_head'])]
def discover(parent):
    # These dev trees contain independent nested clones, not registered git
    # submodules. A '-' from submodule status does not mean sources are absent.
    entries=run(['git','-C',src/parent,'ls-tree','-r','-z','HEAD']).split('\0')
    for entry in entries:
        if not entry: continue
        meta,name=entry.split('\t',1); mode,kind,rev=meta.split()
        if mode!='160000': continue
        rel=parent/name; nested=src/rel
        if not (nested/'.git').exists(): continue
        assert Path(run(['git','-C',nested,'rev-parse','--show-toplevel'])).resolve()==nested.resolve()
        assert run(['git','-C',nested,'rev-parse','HEAD'])==rev,f'Wrong nested HEAD: {rel}'
        assert not run(['git','-C',nested,'status','--porcelain']),f'Dirty nested repository: {rel}'
        repos.append((rel,rev)); discover(rel)
discover(Path('.'))
actual={str(rel):rev for rel,rev in repos[1:]}
for rel,rev in manifest['required_dependency_heads'].items():
    assert actual.get(rel)==rev,f'Missing/wrong required dependency: {rel}'
dest.parent.mkdir()
for rel,rev in repos:
    run(['git','clone','--no-hardlinks','--no-checkout',src/rel,dest/rel])
    run(['git','-C',dest/rel,'checkout','--detach',rev])
run(['git','-C',dest,'apply','--check',payload/'XiangShan-full.patch'])
run(['git','-C',dest,'apply',payload/'XiangShan-full.patch'])
run(['git','-C',dest,'diff','--check'])
for rel,digest in manifest['repaired_sources'].items():
    assert hashlib.sha256((dest/rel).read_bytes()).hexdigest()==digest,rel
(dest.parent/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('VDOT_MTVAL_SOURCE_READY='+str(dest),flush=True)
