"""Repository-local Hello/VADD/VDot-smoke launch and result display."""
from pathlib import Path
import argparse,datetime,json,re,subprocess,sys,uuid
ROOT=Path(__file__).resolve().parents[1]
# Selected log lines may omit the later ANSI reset; display plain text instead.
ANSI_CSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
APPLICATIONS = {'hello':'hello-meijie', 'vadd4':'vadd4', 'vdot-smoke':'vdot-smoke'}

def display_result(out, expected):
    record=json.loads((out/'run-result.json').read_text(encoding='utf8'))
    launch=json.loads((out/'recording-launch.json').read_text(encoding='utf8'))
    if record.get('case')!=expected:
        raise ValueError('Run case does not match the requested result.')
    print('LOG_DIRECTORY='+str(out))
    markers=['Difftest enabled','HIT GOOD TRAP','HIT BAD TRAP','FAIL']
    markers += {'hello-meijie':['hello xiangshan'], 'vadd4':['vadd4:','C[','PASS: vadd'],
                'vdot-smoke':['PASS vdot case=','PASS VDOT_SMOKE']}[expected]
    for line in (out/'run.log').read_text(errors='replace').splitlines():
        line=ANSI_CSI.sub('',line)
        if any(word in line for word in markers):print(line)
    print('EMU_EXIT_CODE='+str(record['exit_code']))
    print('RUNNER_EXIT_CODE='+str(launch['runner_exit_code']))
    passed=record['passed'] and record['exit_code']==0 and launch['runner_exit_code']==0
    print('RUN_CHECK='+('PASS' if passed else 'FAIL'))
    return 0 if passed else 1
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case',choices=APPLICATIONS);ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--result',type=Path,help='Show an exact run directory returned by the launch command')
    args=ap.parse_args()
    if args.result:
        out=args.result.resolve()
        if not out.is_relative_to(ROOT/'runs'):ap.error('Select a run under this repository/runs/.')
        try:return display_result(out,APPLICATIONS[args.case])
        except ValueError as error:ap.error(str(error))
    app=APPLICATIONS[args.case]
    out=ROOT/'runs'/('recording-'+args.case+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    work=ROOT/'work/build'
    argv=[sys.executable,str(ROOT/'tools/run_case.py'),app,'--emu',str(work/'XiangShan/build/emu'),
          '--reference',str(work/'NEMU/build/riscv64-nemu-interpreter-so'),
          '--image',str(work/'nexus-am/apps'/app/'build'/f'{app}-riscv64-xs.bin'),
          '--output',str(out),'--max-cycles','3000000','--timeout','1800']
    print('Run directory: '+str(out),flush=True)
    print('ARGV='+json.dumps(argv,ensure_ascii=False),flush=True)
    if args.dry_run:argv.append('--dry-run')
    result=subprocess.run(argv,cwd=ROOT)
    if not args.dry_run and out.is_dir():
        (out/'recording-launch.json').write_text(json.dumps({'argv':argv,'runner_exit_code':result.returncode},ensure_ascii=False,indent=2)+'\n')
    if args.case=='vdot-smoke' and not args.dry_run and (out/'run-result.json').is_file():
        shown=display_result(out,app)
        return result.returncode or shown
    print('RUNNER_EXIT_CODE='+str(result.returncode),flush=True)
    return result.returncode
if __name__=='__main__':raise SystemExit(main())
