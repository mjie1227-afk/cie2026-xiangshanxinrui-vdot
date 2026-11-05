"""Open a repository waveform and its saved GTKWave view; never runs simulation."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=['1','3']);ap.add_argument('view')
    ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
    views=ROOT/f'recording/stage{args.stage}/views'
    allowed={p.stem for p in views.glob('*.gtkw')}
    if args.view not in allowed:ap.error('Available views: '+', '.join(sorted(allowed)))
    name='vadd4' if args.stage=='1' else 'vdot-mixed' if args.view.startswith('mixed') else 'vdot-cancel'
    vcd=ROOT/'work/waveforms'/f'{name}.vcd';view=views/(args.view+'.gtkw')
    if not vcd.exists():ap.error(f'First run tools/prepare_recording.py --only {name}')
    native=shutil.which('gtkwave')
    windows=Path('C:/iverilog/gtkwave/bin/gtkwave.exe') if sys.platform=='win32' else Path('/mnt/c/iverilog/gtkwave/bin/gtkwave.exe')
    if windows.exists():
        exe=str(windows)
        def converted(p):
            if sys.platform=='win32':return str(p)
            return subprocess.check_output(['wslpath','-w',str(p)],text=True).strip()
        paths=[converted(vcd),converted(view)]
    elif native:exe=native;paths=list(map(str,[vcd,view]))
    else:ap.error('GTKWave not found; install it or use the paths printed in recording/README.md.')
    argv=[exe,'--dump',paths[0],'--save',paths[1]]
    print(json.dumps({'vcd':str(vcd),'view':str(view),'argv':argv},ensure_ascii=False,indent=2))
    if not args.check_only:subprocess.Popen(argv,cwd=ROOT)
    return 0
if __name__=='__main__':raise SystemExit(main())
