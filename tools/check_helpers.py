"""Check packaging helpers with synthetic logs and mock processes, without hardware."""
from pathlib import Path
import importlib.util,json,os,platform,signal,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]

def main():
 if sys.platform!='linux':
  print('Run these process checks in Linux/Ubuntu WSL.',file=sys.stderr);return 2
 spec=importlib.util.spec_from_file_location('runner',ROOT/'tools/run_case.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 checks=[];reference='/tmp/mock-reference.so';marker=mod.MARKERS['vdot-smoke']
 good=f'The reference model is {reference}\nDifftest enabled.\n{marker}\nHIT GOOD TRAP\n'
 cases=[('complete-success',good,0,True),('nonzero-process-exit',good,1,False),('missing-DiffTest',good.replace('Difftest enabled.',''),0,False),('missing-GOOD-TRAP',good.replace('HIT GOOD TRAP',''),0,False),('missing-app-PASS',good.replace(marker,''),0,False),('wrong-reference',good.replace(reference,'/tmp/other.so'),0,False),('failure-marker',good+'FAIL mismatch\n',0,False),('timeout',good,124,False)]
 for name,log,code,expected in cases:
  checks.append({'name':name,'passed':mod.assess(log,code,marker,reference)[1]==expected})
 tmp=Path(tempfile.mkdtemp(prefix='vdot-helper-check-'))
 r=subprocess.run([sys.executable,str(ROOT/'tools/run_case.py'),'vdot-smoke','--emu',str(tmp/'missing'),'--reference',str(tmp/'missing-ref'),'--image',str(tmp/'missing-image'),'--output',str(tmp/'missing-run')],capture_output=True)
 checks.append({'name':'missing-input-refused','passed':r.returncode!=0 and not (tmp/'missing-run').exists(),'exit':r.returncode})
 r=subprocess.run([sys.executable,str(ROOT/'tools/restore_sources.py'),str(tmp)],capture_output=True)
 checks.append({'name':'existing-restore-directory-refused','passed':r.returncode!=0 and not list(tmp.iterdir()),'exit':r.returncode})
 r=subprocess.run(['bash','-n',str(ROOT/'tools/build.sh')],capture_output=True)
 checks.append({'name':'build-shell-syntax','passed':r.returncode==0,'exit':r.returncode})
 # These tiny stand-ins exercise subprocess handling, not the processor or NEMU.
 for mode,expected_code in [('success',0),('failure',9),('timeout',124),('interrupt',130)]:
  case=tmp/mode;case.mkdir();emu=case/'mock-emu';ref=case/'mock-reference.so';img=case/'mock-image.bin';ref.write_bytes(b'mock');img.write_bytes(b'mock')
  emu.write_text('#!/usr/bin/env python3\nimport os,sys,time\nfrom pathlib import Path\nPath("mock.pid").write_text(str(os.getpid()))\nref=next(x.split("=",1)[1] for x in sys.argv if x.startswith("--diff="))\nprint("The reference model is "+ref,flush=True)\nprint("Difftest enabled.",flush=True)\nprint('+repr(marker)+',flush=True)\nprint("HIT GOOD TRAP",flush=True)\n'+('time.sleep(60)\n' if mode in ['timeout','interrupt'] else '')+('sys.exit(9)\n' if mode=='failure' else ''))
  emu.chmod(0o755);out=case/'run'
  argv=[sys.executable,str(ROOT/'tools/run_case.py'),'vdot-smoke','--emu',str(emu),'--reference',str(ref),'--image',str(img),'--output',str(out),'--timeout','1' if mode=='timeout' else '60']
  p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  if mode=='interrupt':
   for _ in range(100):
    if (out/'mock.pid').exists() or p.poll() is not None:break
    time.sleep(0.05)
   p.send_signal(signal.SIGINT)
  stdout,stderr=p.communicate(timeout=20)
  record=json.loads((out/'run-result.json').read_text());child=int((out/'mock.pid').read_text())
  try:os.kill(child,0);child_stopped=False
  except ProcessLookupError:child_stopped=True
  ok=record['exit_code']==expected_code and record['passed']==(mode=='success') and p.returncode==(0 if mode=='success' else 1) and child_stopped
  checks.append({'name':'mock-process-'+mode,'passed':ok,'runner_exit':p.returncode,'recorded_exit':record['exit_code'],'child_stopped':child_stopped})
 result={'scope':'Synthetic logs and mock-process handling only; no processor build or simulation.','cwd':str(ROOT),'argv':[sys.executable,str(Path(__file__).resolve())],'python':platform.python_version(),'temporary_records':str(tmp),'checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks)}
 print(json.dumps(result,ensure_ascii=False,indent=2));return int(bool(result['failed']))
if __name__=='__main__':raise SystemExit(main())
