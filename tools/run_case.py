"""Run one already-built application with explicit emu, NEMU and Flash identities."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,signal,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
MARKERS={
 'hello-meijie':'hello xiangshan, I am Meijie, IP address: 172.26.232.122',
 'vadd4':'PASS: vadd.vv produced [11, 22, 33, 44]',
 'vdot-smoke':'PASS VDOT_SMOKE cases=7',
 'vdot-exceptions':'PASS VDOT_EXCEPTIONS cases=64 traps=62 legal=2',
 'vdot-overlap':'PASS VDOT_OVERLAP cases=60 partitions=15',
 'vdot-deps':'PASS VDOT_DEPS cases=48 programs=12',
 'vdot-mixed':'PASS VDOT_MIXED cases=32 programs=8',
 'vdot-cancel-csr':'PASS VDOT_CANCEL_CSR cases=40 branch=32 precise_trap=8',
 'vdot-port-contend-v1':'PASS VDOT_PORT_CANDIDATE',
 'vdot-rvv-equiv-v1':'PASS VDOT_RVV_EQUIV cases=144 kernels=432 baselines=2',
 'vdot-timing-pilot-v1':'PASS VDOT_TIMING_PILOT calls=42 samples=36 warmups=6',
 'vdot-chain-v1':'PASS VDOT_CHAIN calls=40 samples=30 warmups=10',
 'vdot-throughput-v1':'PASS VDOT_TPUT calls=40 samples=30 warmups=10',
 'vdot-e2e-v1':'PASS VDOT_E2E calls=40 samples=30 warmups=10',
 'vdot-segment-v1':'PASS VDOT_SEG calls=52 samples=39 warmups=13',
 'vdot-load-v1':'PASS VDOT_OPT_LOAD calls=98 samples=63 warmups=35',
 'vdot-tile-v1':'PASS VDOT_OPT_TILE calls=70 samples=45 warmups=25'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def assess(log,code,marker,reference):
 checks={'process_exit_zero':code==0,'application_marker':marker in log,'difftest_enabled':'Difftest enabled.' in log,'good_trap':'HIT GOOD TRAP' in log,'reference_path':f'The reference model is {reference}' in log,'no_failure_marker':not any(x in log for x in ['HIT BAD TRAP','ABORT','different at pc','FAIL'])}
 return checks,all(checks.values())

def stop_process_group(process):
 try:os.killpg(process.pid,signal.SIGTERM)
 except ProcessLookupError:return
 try:process.wait(timeout=10)
 except subprocess.TimeoutExpired:
  try:os.killpg(process.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  process.wait()
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('case',choices=MARKERS);ap.add_argument('--emu',type=Path,required=True);ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--image',type=Path,required=True)
 ap.add_argument('--flash',type=Path,default=ROOT/'configs/boot-flash.bin');ap.add_argument('--output',type=Path,required=True,help='New run directory; must not exist')
 ap.add_argument('--seed',type=int,default=1);ap.add_argument('--max-cycles',type=int,default=20000000);ap.add_argument('--timeout',type=int,default=7200);ap.add_argument('--dry-run',action='store_true')
 a=ap.parse_args()
 paths={k:getattr(a,k).expanduser().resolve() for k in ['emu','reference','image','flash']}
 for k,p in paths.items():
  if not p.is_file():ap.error(f'Missing {k}: {p}')
 if a.max_cycles<=0 or a.timeout<=0:ap.error('Cycle and wall-time limits must be positive.')
 out=a.output.expanduser().resolve()
 if out.exists():ap.error(f'Run directory already exists: {out}')
 if not os.access(paths['emu'],os.X_OK):ap.error('Emulator is not executable.')
 argv=[str(paths['emu']),'-i',str(paths['image']),'--diff='+str(paths['reference']),'-F',str(paths['flash']),'--seed='+str(a.seed),'--max-cycles='+str(a.max_cycles),'--no-snapshot']
 identities={k:{'path':str(p),'sha256':sha(p)} for k,p in paths.items()}
 if a.dry_run:
  print(json.dumps({'argv':argv,'cwd':str(out),'identities':identities,'status':'inputs checked; not executed'},indent=2));return 0
 if sys.platform!='linux':ap.error('Execute the simulator in Linux/Ubuntu WSL.')
 out.mkdir(parents=True);(out/'build').mkdir()
 env=dict(os.environ,NOOP_HOME=str(out))
 record={'case':a.case,'argv':argv,'cwd':str(out),'environment':{'NOOP_HOME':str(out)},'seed':a.seed,'cycle_limit':a.max_cycles,'wall_timeout_seconds':a.timeout,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'identities':identities,'log':'run.log'}
 (out/'run-result.json').write_text(json.dumps(record,indent=2))
 with (out/'run.log').open('wb') as f:
  p=subprocess.Popen(argv,cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:code=p.wait(timeout=a.timeout)
  except subprocess.TimeoutExpired:
   stop_process_group(p)
   code=124
  except KeyboardInterrupt:
   stop_process_group(p)
   code=130
 log=(out/'run.log').read_text(errors='replace');checks,passed=assess(log,code,MARKERS[a.case],paths['reference'])
 record.update(exit_code=code,checks=checks,passed=passed,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),log_sha256=sha(out/'run.log'))
 (out/'run-result.json').write_text(json.dumps(record,indent=2));(out/'exit-code.txt').write_text(str(code)+'\n')
 print(json.dumps({'passed':passed,'exit_code':code,'checks':checks,'run_directory':str(out)},indent=2))
 return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
