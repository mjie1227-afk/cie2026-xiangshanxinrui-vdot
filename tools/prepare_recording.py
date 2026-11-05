"""Expand the three included historical waveform archives inside work/waveforms."""
from pathlib import Path
import argparse, gzip, hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()
class ArchiveParts:
    """Sequential read across lossless gzip volumes, without a temporary concatenation."""
    def __init__(self, paths):
        self.paths=iter(paths);self.current=None
    def read(self, size=-1):
        if size<0:raise ValueError('Unbounded archive read is not supported')
        chunks=[];left=size
        while left:
            if self.current is None:
                path=next(self.paths,None)
                if path is None:break
                self.current=path.open('rb')
            chunk=self.current.read(left)
            if not chunk:self.current.close();self.current=None;continue
            chunks.append(chunk);left-=len(chunk)
        return b''.join(chunks)
    def close(self):
        if self.current:self.current.close()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', choices=['vadd4','vdot-cancel','vdot-mixed'])
    ap.add_argument('--check-only', action='store_true')
    args=ap.parse_args()
    items=json.loads((ROOT/'recording/waveforms.json').read_text())['waveforms']
    for item in items:
        if args.only and item['id']!=args.only:continue
        archives=[ROOT/p['path'] for p in item['archives']]; target=ROOT/item['output']
        for source,part in zip(archives,item['archives']):
            if digest(source)!=part['sha256']:raise ValueError('Archive mismatch: '+str(source))
        if target.exists():
            if target.stat().st_size!=item['bytes'] or digest(target)!=item['sha256']:
                raise ValueError('Existing VCD differs; preserved without overwrite: '+str(target))
            print('WAVE_ALREADY_READY',target);continue
        if args.check_only:
            print('ARCHIVE_OK',len(archives),'volume(s)','->',target);continue
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix('.vcd.partial')
        if temporary.exists():raise ValueError('Previous partial file exists: '+str(temporary))
        h=hashlib.sha256();count=0
        stream=ArchiveParts(archives)
        try:
            with gzip.GzipFile(fileobj=stream,mode='rb') as f,temporary.open('xb') as g:
                for block in iter(lambda:f.read(4*1024*1024),b''):
                    g.write(block);h.update(block);count+=len(block)
        finally:stream.close()
        if count!=item['bytes'] or h.hexdigest()!=item['sha256']:
            raise ValueError('Decompressed VCD mismatch; partial file preserved: '+str(temporary))
        temporary.rename(target)
        print('WAVE_READY',target)
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError) as e:print(e,file=sys.stderr);raise SystemExit(1)
