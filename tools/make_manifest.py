"""Regenerate the delivery manifest after intentional changes, such as video links."""
import sys
sys.dont_write_bytecode=True
from verify_bundle import ROOT,bundle_files,sha
files=[p for p in bundle_files() if p.name!='MANIFEST.sha256']
for p in files:
 if p.name=='my_submission.txt' or p.suffix in ['.vcd','.fst'] or p.stat().st_size>=100*1024*1024:
  raise SystemExit('Remove unintended/oversized file before making a manifest: '+str(p))
(ROOT/'MANIFEST.sha256').write_text(''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files),encoding='utf8')
print('MANIFEST_WRITTEN',len(files))
