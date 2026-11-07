"""Offline verification of this delivery bundle; does not build or simulate hardware."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import hashlib,json,os,re,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

LOCAL_DIR_NAMES={'.git','.metals','.scala-build','.bloop','.bsp','__pycache__'}
EXTERNAL_VIDEO_SUFFIXES={'.mp4','.mkv','.mov','.webm','.avi'}
LOCAL_PREFIXES={('work',),('runs',),('build',),('target',),('recording','outputs'),('src','XiangShan','out')}

def local_directory(parts):
 return (any(part in LOCAL_DIR_NAMES for part in parts)
         or any(tuple(parts[:len(prefix)])==prefix for prefix in LOCAL_PREFIXES)
         or (len(parts)>=3 and parts[0]=='apps' and parts[2]=='build'))

def bundle_files():
 # Prune IDE/build caches before traversal; never enumerate or package their files.
 files=[]
 for directory,dirs,names in os.walk(ROOT,followlinks=False):
  parent=Path(directory);parts=parent.relative_to(ROOT).parts
  dirs[:]=[name for name in dirs if not local_directory(parts+(name,))]
  for name in names:
   p=parent/name
   # LFS video bodies are downloaded separately from the build payload.
   # Keep the viewing instructions in the source bundle.
   if parts and parts[0]=='videos' and p.suffix.lower() in EXTERNAL_VIDEO_SUFFIXES:continue
   if not name.endswith('.pyc') and p.is_file():files.append(p)
 return sorted(files,key=lambda p:p.relative_to(ROOT).as_posix())
def main():
 errors=[];count=0;listed=set()
 manifest=ROOT/'MANIFEST.sha256'
 has_manifest=manifest.is_file()
 if has_manifest:
  for line in manifest.read_text(encoding='utf8').splitlines():
   digest,rel=line.split('  ',1);p=ROOT/rel;count+=1;listed.add(rel)
   if not p.is_file() or sha(p)!=digest:errors.append({'kind':'file checksum','file':rel})
 lock=json.loads((ROOT/'configs/source-snapshots.json').read_text())
 for name,files in lock.items():
  for rel,digest in files.items():
   p=ROOT/'src'/name/rel
   if not p.is_file() or sha(p)!=digest:errors.append({'kind':'source snapshot','file':str(p.relative_to(ROOT))})
 source_tree=json.loads((ROOT/'configs/source-tree.json').read_text(encoding='utf8'))
 for entry in source_tree['entries']:
  p=ROOT/entry['stored']
  if not p.is_file() or sha(p)!=entry['sha256']:errors.append({'kind':'complete source','file':entry['stored']})
  if has_manifest and entry['stored'] not in listed:errors.append({'kind':'source omitted from manifest','file':entry['stored']})
 files=bundle_files()
 links=0
 for p in files:
  if p.suffix.lower()!='.md' or p.relative_to(ROOT).parts[0]=='src':continue
  txt=p.read_text(encoding='utf-8-sig')
  clean=re.sub(r'^```[^\n]*\n[\s\S]*?^```\s*$','',txt,flags=re.M)
  if len(re.findall(r'^```',txt,re.M))%2:errors.append({'kind':'unclosed code fence','file':str(p.relative_to(ROOT))})
  for raw in re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)',clean):
   raw=raw.strip('<>');u=urlsplit(raw)
   if u.scheme or not u.path:continue
   q=(p.parent/unquote(u.path)).resolve();links+=1
   if not q.is_relative_to(ROOT) or not q.exists():errors.append({'kind':'local link','file':str(p.relative_to(ROOT)),'target':raw})
 if has_manifest:
  for rel in sorted({p.relative_to(ROOT).as_posix() for p in files}-listed-{'MANIFEST.sha256'}):
   errors.append({'kind':'unlisted file','file':rel})
 for p in files:
  if p.stat().st_size>=100*1024*1024:errors.append({'kind':'GitHub file size','file':str(p.relative_to(ROOT))})
  if p.name in ['my_submission.txt'] or p.suffix in ['.vcd','.fst']:errors.append({'kind':'unintended upload','file':str(p.relative_to(ROOT))})
 for app in json.loads((ROOT/'configs/apps.json').read_text())['applications']:
  p=ROOT/'apps'/app/'Makefile'
  if not p.is_file():errors.append({'kind':'application Makefile','file':app});continue
  m=re.search(r'^SRCS\s*=\s*(.*)$',p.read_text(),re.M)
  if not m:errors.append({'kind':'application SRCS','file':app});continue
  for name in m[1].split():
   if not (p.parent/name).is_file():errors.append({'kind':'application source missing','file':app+'/'+name})
 result={'status':'bundle-check-passed' if not errors else 'bundle-check-failed','scope':'File, source and documentation checks only; no hardware execution.','manifest_files':count,'complete_source_entries':len(source_tree['entries']),'local_links':links,'files':len(files),'total_bytes':sum(p.stat().st_size for p in files),'largest_file_bytes':max(p.stat().st_size for p in files),'errors':errors}
 print(json.dumps(result,ensure_ascii=False,indent=2));return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())

