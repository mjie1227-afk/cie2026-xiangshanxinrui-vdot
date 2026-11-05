"""Verify the downloaded Git LFS recordings using the published video manifest."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]

def verify(root):
    directory=root/'videos';manifest=json.loads((directory/'manifest.json').read_text(encoding='utf8'))
    results=[]
    for entry in manifest['videos']:
        name=entry['filename'];p=(directory/name).resolve();error=None
        if not p.is_relative_to(directory.resolve()):error='unsafe video filename'
        elif not p.is_file():error='missing video; run git lfs pull'
        else:
            with p.open('rb') as f:prefix=f.read(200)
            if prefix.startswith(b'version https://git-lfs.github.com/spec/v1'):error='LFS pointer only; run git lfs pull'
            elif p.stat().st_size!=entry['bytes']:error='video size differs from manifest'
            else:
                h=hashlib.sha256()
                with p.open('rb') as f:
                    for data in iter(lambda:f.read(4*1024*1024),b''):h.update(data)
                if h.hexdigest()!=entry['sha256']:error='video SHA256 differs from manifest'
        results.append({'file':name,'ok':error is None,'error':error})
    if not results:results.append({'file':'manifest.json','ok':False,'error':'no videos listed'})
    return results

def main():
    try:results=verify(ROOT)
    except (OSError,ValueError,KeyError) as e:
        print('VIDEOS_CHECK=FAIL',str(e));return 1
    for r in results:print(('OK' if r['ok'] else 'FAIL')+' '+r['file']+((': '+r['error']) if r['error'] else ''))
    passed=all(r['ok'] for r in results)
    print('VIDEOS_CHECK='+('PASS' if passed else 'FAIL'));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
