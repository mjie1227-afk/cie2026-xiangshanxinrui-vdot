"""Validate the frontend report addition against preserved files and samples.

Reads reports, sources, images and archived JSON. Writes only check-result.json
in this directory. Does not run simulation or synchronize native directories.
"""
import hashlib,json,platform,re,sys
from pathlib import Path
from urllib.parse import unquote
from PIL import Image

OUT=Path(__file__).resolve().parent
EVIDENCE=OUT.parent
ROOT=EVIDENCE.parents[1]
REPORT=ROOT/'reports/stage1/vadd-lifecycle.md'
def read_json(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
errors=[];checks=[]
def check(name,ok,detail=None):
    checks.append({'name':name,'passed':bool(ok),'detail':detail})
    if not ok:errors.append(name)

old=(OUT/'before/vadd-lifecycle.md').read_text(encoding='utf-8-sig')
new=REPORT.read_text(encoding='utf-8-sig')
def section(t,start,end):return t[t.index(start):t.index(end)]
body=section(new,'### 3.2 译码','## 4 实验结论')
body=re.sub(r'^(### 3\.)([2-8])(\s)',lambda m:m[1]+str(int(m[2])-1)+m[3],body,flags=re.M)
body=re.sub(r'图(\s*)(\d+)',lambda m:'图'+m[1]+str(int(m[2])-6),body)
check('Original backend text preserved except numbering',body==section(old,'### 3.1 译码','## 4 实验结论'))
check('Original build/run appendix unchanged',section(old,'## 附录 A','## 附录 B')==section(new,'## 附录 A','## 附录 B'))
image_rx=r'!\[图(\d+)[^\]]*\]\((assets/vadd/[^)]+)\)'
images=re.findall(image_rx,new)
check('Sixteen image labels in reading order',[int(n) for n,p in images]==list(range(1,17)))
captions=[int(n) for n in re.findall(r'^\*\*图 (\d+)\s',new,re.M)]
check('Sixteen captions in reading order',captions==list(range(1,17)))
check('All figures retained in report body',all(new.index(']('+p+')')<new.index('## 附录 A') for n,p in images))
manifest=read_json(EVIDENCE/'report-images.json')
for path,expected in manifest['original_images'].items():
    check('Original image unchanged: '+path,sha(REPORT.parent/path)==expected)
image_details=[]
for n,path in images:
    p=REPORT.parent/path
    with Image.open(p) as im:
        dimensions=im.size;im.verify()
    image_details.append({'figure':int(n),'path':path,'dimensions':dimensions,'sha256':sha(p)})
for entry in manifest['frontend_images']:
    check('Frontend image exact copy: '+entry['report_image'],
        sha(REPORT.parent/entry['report_image'])==sha(ROOT/entry['source'])==entry['sha256'])
latest=read_json(EVIDENCE/'decode-bridge-user-confirmation.json')
for e in latest['images']:
    check('User original screenshot unchanged: '+str(e['marker_ps']),sha(Path(e['source_image']))==e['sha256'])

ftq=read_json(EVIDENCE/'ftq-request-observations.json')
row=next(x for x in ftq['samples'] if x['time_ps']==5079)['signals_hex']
for name,val in {'io_toIfu_req_valid':1,'io_toIfu_req_ready':1,'io_toIfu_req_bits_ftqIdx_flag':0,
    'io_toIfu_req_bits_ftqIdx_value':3,'io_toIfu_req_bits_startAddr':0x80000134,'io_toIfu_req_bits_nextStartAddr':0x80000154}.items():
    check('FTQ5079 '+name,int(row[name],16)==val)
cache=read_json(EVIDENCE/'icache-response-observations.json')
row=next(x for x in cache['samples'] if x['time_ps']==5083)['signals_hex']
prefix='TOP.SimTop.l_soc.core_with_l2.core.frontend.inner_icache.'
for name,val in {'io_fetch_resp_valid':1,'io_fetch_resp_bits_vaddr_0':0x80000134,
    'io_fetch_resp_bits_doubleline':1,'io_fetch_resp_bits_exception_0':0,'io_fetch_resp_bits_exception_1':0}.items():
    check('ICache5083 '+name,int(row[prefix+name],16)==val)
data=int(row[prefix+'io_fetch_resp_bits_data'],16)
check('ICache target bits95:64',((data>>64)&0xffffffff)==0x021101d7)
check('ICache low128 grouping',f'{data&((1<<128)-1):032x}'=='020661a7021101d70205e10702056087')
layout=read_json(EVIDENCE/'icache-data-layout.json')['signals_hex']
copy_data=(data<<512)|data
ptr10=int(layout['f2_cut_ptr_10'],16);ptr11=int(layout['f2_cut_ptr_11'],16)
word=((copy_data>>(ptr11*16))&0xffff)<<16|((copy_data>>(ptr10*16))&0xffff)
check('IFU cut pointers select target',ptr10==36 and ptr11==37 and word==0x021101d7)
check('FTQ block offset is target halfword10',(0x80000148-0x80000134)//2==10)
check('IFU valid/enqueue masks include slot10',bool(0xd555&(1<<10)))

bridge=read_json(EVIDENCE/'decode-bridge-observations.json')
check('Bridge VCD identity',bridge['sha256']=='01dc7a20fcfd416acfb1c9874759ac460d8e7b6144d608e865da4a2d168059b8')
def at(time,key):return next(x for x in bridge['samples'] if x['time_ps']==time)['scopes'][key]
ctrl=at(5087,'ctrl');dec=at(5087,'decode')
check('Backend input ready while decode waits',ctrl['io_frontend_cfVec_5_valid']=='0x1' and ctrl['io_frontend_cfVec_5_ready']=='0x1' and dec['io_in_5_valid']=='0x1' and dec['io_in_5_ready']=='0x0')
check('Two initial entries accepted',ctrl['decodeFromFrontendAcceptNum']=='0x2')
for time,lane in [(5088,3),(5089,3),(5090,1),(5091,1),(5092,0),(5093,0),(5111,0)]:
    c=at(time,'ctrl')
    want={f'decodeBufValid_{lane}':1,f'decodeBufBits_{lane}_pc':0x80000148,
          f'decodeBufBits_{lane}_instr':0x021101d7,f'decodeBufBits_{lane}_ftqPtr_flag':0,
          f'decodeBufBits_{lane}_ftqPtr_value':3,f'decodeBufBits_{lane}_ftqOffset':10}
    check(f'Buffer target identity {time} lane{lane}',all(int(c[n],16)==v for n,v in want.items()))
check('No flush or decode redirect in bridge window',all(x['scopes']['ibuffer']['io_flush']=='0x0' and x['scopes']['decode']['io_redirect']=='0x0' for x in bridge['samples']))
check('Decode acceptance pre-edge',at(5111,'decode')['io_in_0_valid']=='0x1' and at(5111,'decode')['io_in_0_ready']=='0x1')
check('Correct valid clears at5112',at(5112,'ctrl')['decodeBufValid_0']=='0x0' and at(5112,'decode')['io_in_0_valid']=='0x1')
check('Next instruction displayed at5112',at(5112,'decode')['io_in_0_bits_pc']=='0x8000014c' and at(5112,'decode')['io_in_0_bits_instr']=='0x20661a7')

source=read_json(EVIDENCE/'report-source-evidence.json')
srcroot=Path(r'D:\Mayyyyyy\WorkSpaces\VScode\xs-env\XiangShan')
for path,expected in source['files'].items():check('Source hash: '+path,sha(srcroot/path)==expected)
check('Source HEAD matches report run','16ae9ddcda54fc9a2fddffad73174cf793ac7814' in source['commands'][0]['stdout'])
check('Source status and related diff empty',all(x['exit_code']==0 and not x['stdout'] for x in source['commands'][1:]))

# Inspect all project-owned Markdown entries, without walking external snapshots.
docs=sorted(set(ROOT.glob('*.md'))|set((ROOT/'docs').rglob('*.md'))|set((ROOT/'reports').rglob('*.md'))|
            set((ROOT/'exercises/vadd4').glob('*.md')))
changed={x['file'] for x in read_json(OUT/'document-changes.json')}
inventory=[];links=[]
result_path=OUT/'check-result.json'
for p in docs:
    rel=p.relative_to(ROOT).as_posix();t=p.read_text(encoding='utf-8-sig')
    inventory.append({'file':rel,'status':'updated' if rel in changed else 'reviewed, unchanged',
                      'reason':'Frontend report/state/navigation' if rel in changed else 'Outside frontend extension; existing dated scope retained'})
    if rel not in changed:continue
    check('Code fences paired: '+rel,t.count('```')%2==0)
    t=re.sub(r'```[^\n]*\n.*?```','',t,flags=re.S)
    for m in re.finditer(r'!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)',t):
        target=m[1].strip('<>').split('#',1)[0]
        if not target or target.startswith(('https://','http://','mailto:')):continue
        dest=(p.parent/unquote(target)).resolve()
        exists=dest.exists() or dest==result_path.resolve()
        links.append({'document':rel,'target':target,'exists':exists})
        if not exists:errors.append('Broken local link: '+rel+' -> '+target)
check('Evidence rows remain in a single table',bool(re.search(r'^\| V6[^\n]*\n\| V7[^\n]*\n\| V8',new,re.M)))
check('No contradictory pending frontend status in current intro','尚未' not in section(new,'### 3.1 前端','### 3.2 译码').split('\n\n')[1])
result={'date':'2026-10-19','timezone':'Asia/Shanghai','scope':'Document and archived-evidence check; no RTL simulation',
        'invocation':{'argv':[sys.executable,str(Path(__file__).resolve())],'cwd':str(ROOT),'python':platform.python_version(),'exit_code':0 if not errors else 1},
        'report_sha256':sha(REPORT),'checks':checks,'check_count':len(checks),'images':image_details,
        'inventory':inventory,'local_links':links,'local_link_count':len(links),'errors':errors,'passed':not errors}
result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':not errors,'checks':len(checks),'images':len(images),'local_links':len(links),'errors':errors},ensure_ascii=True))
sys.exit(0 if not errors else 1)
