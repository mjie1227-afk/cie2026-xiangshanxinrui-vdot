"""Render candidates and three self-contained stage volumes; no DUT execution."""
from pathlib import Path
from urllib.parse import unquote
import base64, hashlib, html, json, os, re, sys
from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FINAL=ROOT/'docs_final'
OUT=FINAL/'合订版'; OUT.mkdir(exist_ok=True)
PREVIEW=HERE/'preview';PREVIEW.mkdir(exist_ok=True)
MD=MarkdownIt('commonmark',{'html':True}).enable('table')
CHAPTERS=[
('01_赛题与总体方案/赛题要求与提交材料对照.md',1),
('01_赛题与总体方案/vdot.vv语义合同与总体方案.md',2),
('02_阶段一_环境与基础分析/环境部署与运行验证.md',3),
('02_阶段一_环境与基础分析/VADD指令全生命周期波形分析.md',4),
('03_阶段二_指令设计与RTL实现/vdot微架构与数据通路设计.md',5),
('03_阶段二_指令设计与RTL实现/香山整核集成与关键控制路径.md',6),
('03_阶段二_指令设计与RTL实现/功能测试与微架构时序验证.md',7),
('04_阶段三_协同仿真与性能剖析/NEMU扩展与DiffTest协同验证.md',8),
('04_阶段三_协同仿真与性能剖析/标准RVV等价基线设计与验证.md',9),
('04_阶段三_协同仿真与性能剖析/分层性能测量与分析.md',10)]
chap={ (FINAL/p).resolve():n for p,n in CHAPTERS}
VOLUMES=[('阶段一_环境与执行过程','位置 ① · 官方 1.1、1.2、1.3',[3,4],['第一阶段复现环境、产物哈希与材料路径索引.md']),
('阶段二_设计与基础测试','位置 ② · 官方 2.1、2.2、2.3.1～2.3.3',[2,5,6,7],['第二阶段复现环境、产物哈希与材料路径索引.md']),
('阶段三_协同仿真与性能分析','位置 ③ · 官方 3.1.1、3.1.2、3.2、3.3',[8,9,10],['第三阶段复现环境、产物哈希与材料路径索引.md'])]
CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#eef2f5;color:#243747;font-family:"Microsoft YaHei",sans-serif;line-height:1.8}main{max-width:1180px;margin:24px auto;padding:32px 44px 60px;background:white}h1{font-size:29px;line-height:1.4;margin:18px 0 24px}h2{font-size:23px;border-bottom:1px solid #cddbe5;padding-top:12px;margin-top:32px}h3{font-size:19px;margin-top:26px}h4{font-size:17px}p,li{font-size:16px}li{margin:5px 0}a{color:#146787;text-decoration:none;overflow-wrap:anywhere}a:hover{text-decoration:underline}table{border-collapse:collapse;width:100%;table-layout:auto;margin:16px 0 25px}th,td{border:1px solid #cedbe4;padding:8px 10px;text-align:left;font-size:14px;vertical-align:top;overflow-wrap:anywhere}th{background:#edf4f7}td[style*="text-align:right"],th[style*="text-align:right"]{white-space:nowrap}pre{background:#f2f6f8;border-left:3px solid #2d728f;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65;font-size:13px}code{font-family:Consolas,"Microsoft YaHei",monospace;overflow-wrap:anywhere}img{max-width:100%;height:auto;display:block;margin:18px auto 8px}figure{margin:22px 0}figcaption{font-size:14px;color:#455f70;line-height:1.65}blockquote{border-left:3px solid #7699aa;padding-left:15px;margin:18px 0;color:#45616f}nav{font-size:14px;border-bottom:1px solid #dce5eb;padding-bottom:14px}nav a{margin-right:20px}hr{border:0;border-top:1px solid #dce5eb;margin:28px 0}.cover{padding-bottom:25px}.chapter{margin-top:50px}.source-ref{color:#536a77;font-size:0.9em;overflow-wrap:anywhere}.toc{padding:20px;background:#f3f7fa}.toc li{margin:8px 0}'''
CSS+='''@page{size:A4;margin:18mm 15mm 17mm}@media print{body{background:white;line-height:1.65}main{margin:0;padding:0;max-width:none}nav{display:none}.cover{break-after:page}.chapter{break-before:page;margin-top:0}h1{font-size:22pt}h2{font-size:16pt;margin-top:20px}h3{font-size:13pt}h4{font-size:11pt}p,li{font-size:10pt}td,th{font-size:8.5pt;padding:5px 6px}table{margin:10px 0 16px;break-inside:avoid;break-before:avoid}thead{display:table-header-group}tr{break-inside:avoid}pre{font-size:7.8pt;line-height:1.5;padding:9px;break-inside:auto}figure{break-inside:avoid;margin:12px 0}figure img{max-height:195mm;object-fit:contain}figcaption{font-size:8.5pt}h1,h2,h3,h4,.table-caption{break-after:avoid}.wave-evidence{break-inside:avoid}p{orphans:3;widows:3}.source-ref{font-size:8pt}a{color:#146787}blockquote{margin:10px 0}td[style*="text-align:right"]{white-space:normal}}'''
CSS+='''@media print{pre{break-inside:avoid}.materials table{break-inside:auto;break-before:auto}.materials>p{break-after:avoid}.materials th:first-child,.materials td:first-child{width:13mm}.materials td{font-size:8pt}hr{margin:10px 0}}'''

CSS+='''.materials td:last-child code{word-break:break-all}.materials th:nth-child(2){min-width:35mm}.materials table:last-of-type th:nth-child(2){width:40mm}@media print{.materials h1{font-size:20pt}.materials table{break-inside:auto}.materials table:first-of-type th:first-child{width:34mm}.materials table:nth-of-type(2) th:first-child{width:38mm}.materials td:last-child{line-height:1.6}.materials p{break-after:auto}}'''
CSS+='''@media print{.chapter p:has(+ pre){break-after:avoid}.chapter img[alt*="Hello终端"]{max-height:140mm;width:auto}}'''

def slug(s):return re.sub(r'[^\w\s\-\u3400-\u9fff]','',s.lower()).replace(' ','-')
def docid(p):return 'ch'+str(chap[p]) if p in chap else 'd'+hashlib.sha256(str(p.relative_to(FINAL)).encode()).hexdigest()[:10]
def parsed(p):
    ts=MD.parse(p.read_text(encoding='utf-8'))
    seen={}
    for i,t in enumerate(ts[:-1]):
        if t.type=='heading_open':
            s=slug(ts[i+1].content);n=seen.get(s,0);seen[s]=n+1
            t.attrSet('id',s+(f'-{n}' if n else ''))
    return ts
def embed(p):
    ext=p.suffix.lower(); mime={'.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}[ext]
    return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()
def block(p,included=None,refs=None):
    ts=parsed(p);prefix=docid(p)
    for t in ts:
        if t.type=='heading_open' and included is not None:t.attrSet('id',prefix+'-'+t.attrGet('id'))
        for c in t.children or []:
            attr='src' if c.type=='image' else 'href' if c.type=='link_open' else None
            if not attr:continue
            url=c.attrGet(attr)
            if re.match(r'^[A-Za-z]+:',url):continue
            name,sep,anchor=unquote(url).partition('#');q=(p.parent/name).resolve() if name else p
            if attr=='src':c.attrSet(attr,embed(q));continue
            if included is not None:
                if q in included:
                    c.attrSet(attr,'#'+docid(q)+(('-'+anchor) if sep else ''))
                else:
                    # Repository traceability becomes readable text, not a broken offline link.
                    refno=refs.setdefault(q,len(refs)+1)
                    c.type='html_inline';c.tag='';c.content='<span class="source-ref">';c.meta={'offline_ref':refno}
                    # Its matching closing token is converted below, preserving normal child formatting.
            else:
                if q in preview_names:c.attrSet(attr,preview_names[q]+(sep+anchor if sep else ''))
                else:c.attrSet(attr,q.as_uri()+(sep+anchor if sep else ''))
        if t.children and included is not None:
            stack=[]
            for c in t.children:
                if c.meta.get('offline_ref'):stack.append(c.meta['offline_ref'])
                elif c.type=='link_open':stack.append(False)
                elif c.type=='link_close' and stack:
                    refno=stack.pop()
                    if refno:c.type='html_inline';c.tag='';c.content=f'</span><a href="#material-{refno}"><sup>[材料 {refno}]</sup></a>'
    s=MD.renderer.render(ts,MD.options,{})
    if included is not None:s=re.sub(r'(?:<hr\s*/?>\s*)?<p>文档编号：[^<]+</p>','',s)
    s=re.sub(r'<p>(<img [\s\S]*?/>)</p>\s*<p>(图 [^<\n]+[\s\S]*?)</p>',r'<figure>\1<figcaption>\2</figcaption></figure>',s)
    s=re.sub(r'<p>(表 [^\n]+)</p>\s*(?=<table>)',r'<p class="table-caption">\1</p>\n',s)
    s=re.sub(r'(<figure>(?:(?!<figure>)[\s\S])*?</figure>)\s*(<p class="table-caption">[^\n]*(?:关键|读数|身份)[^\n]*</p>\s*<table>[\s\S]*?</table>)',r'<div class="wave-evidence">\1\2</div>',s)
    return s

docs=[(FINAL/'README.md').resolve()]+list(chap)+sorted((FINAL/'附录').glob('*.md'))
docs=[p.resolve() for p in docs]
preview_names={p:('index.html' if p.name=='README.md' else f'{docid(p)}.html') for p in docs}
nav='<nav><a href="index.html">总目录</a><a href="ch5.html">数据通路</a><a href="ch8.html">协同仿真</a><a href="ch10.html">延迟与性能</a></nav>'
for p in docs:
    content=block(p)
    (PREVIEW/preview_names[p]).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+html.escape(p.stem)+'</title><style>'+CSS+'</style><main>'+nav+content+'</main></html>',encoding='utf-8')
volumes=[]
material_indices=json.loads((ROOT/'artifacts/docs-final-reader-revision-2026-10-29/material-index.json').read_text(encoding='utf-8'))
for stage,(name,scope,nums,apps) in enumerate(VOLUMES,1):
    if stage != 3: continue
    members=[p for p,n in chap.items() if n in nums]+[(FINAL/'附录'/x).resolve() for x in apps]
    included=set(members)
    toc=''.join(f'<li><a href="#{docid(p)}">'+(f'第 {chap[p]} 章　' if p in chap else '附录　')+html.escape(p.stem)+'</a></li>' for p in members)
    cover=f'<section class="cover"><p>香山昆明湖 V2 自定义 vdot.vv</p><h1>{name.replace("_","：")}</h1><p>{scope}</p><p>章节与图表沿用总目录第 1～10 章编号。本文收纳对应正文、插图和附录；源码及原始日志通过文中标识与工程材料对应。</p><div class="toc"><strong>目录</strong><ul>{toc}</ul></div></section>'
    cover=cover.replace('本文收纳对应正文、插图和附录；源码及原始日志通过文中标识与工程材料对应。','正文给出技术方法、核心代码和实测结果；文末一份附录集中列出复现环境、产物哈希与工程材料路径。')
    refs={(ROOT/r['path']).resolve():r['number'] for r in material_indices[str(stage)]}
    expected_refs=len(refs)
    content=''.join('<section class="chapter'+(' materials' if p not in chap else '')+'" id="'+docid(p)+'">'+block(p,included,refs)+'</section>' for p in members)
    assert len(refs)==expected_refs,'Material index needs refresh'
    output=OUT/(name+'.html')
    output.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+name+'</title><style>'+CSS+'</style><main>'+cover+content+'</main></html>',encoding='utf-8')
    volumes.append({'name':name,'path':str(output.relative_to(ROOT)),'members':[str(p.relative_to(ROOT)) for p in members]})

checks=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r'C:\Users\Lenovo\AppData\Local\ms-playwright\chromium-1208\chrome-win64\chrome.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
    for p in docs:
        out=PREVIEW/preview_names[p];page.goto(out.as_uri());page.wait_for_load_state('load')
        bad=page.locator('img').evaluate_all('(xs)=>xs.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.alt)')
        overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
        checks.append({'document':str(p.relative_to(ROOT)),'broken_images':bad,'overflow':overflow})
        if p in chap and chap[p] in [3,4,5,7,8,9,10]:page.screenshot(path=str(PREVIEW/(docid(p)+'-top.png')))
    for v in volumes:
        out=ROOT/v['path'];page.goto(out.as_uri());page.wait_for_load_state('load')
        bad=page.locator('img').evaluate_all('(xs)=>xs.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.alt)')
        broken=page.locator('a[href^="#"]').evaluate_all('(xs)=>xs.filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash)')
        external_local=page.locator('a').evaluate_all('(xs)=>xs.map(a=>a.getAttribute("href")).filter(h=>h&&!h.startsWith("#")&&!/^https?:/.test(h))')
        v.update({'broken_images':bad,'broken_anchors':broken,'external_local_links':external_local,'bytes':out.stat().st_size})
        if '--pdf' in sys.argv:
            pdf=out.with_suffix('.pdf')
            page.pdf(path=str(pdf),format='A4',print_background=True,display_header_footer=True,header_template='<div></div>',footer_template='<div style="font:8px Arial;color:#64727a;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',prefer_css_page_size=True)
            v['pdf']=str(pdf.relative_to(ROOT))
    browser.close()
(HERE/'render-check.json').write_text(json.dumps({'documents':checks,'volumes':volumes},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'previews':len(docs),'volumes':len(volumes),'render_errors':sum(bool(c['broken_images'] or c['overflow']) for c in checks)+sum(bool(v['broken_images'] or v['broken_anchors'] or v['external_local_links']) for v in volumes)},ensure_ascii=False))
