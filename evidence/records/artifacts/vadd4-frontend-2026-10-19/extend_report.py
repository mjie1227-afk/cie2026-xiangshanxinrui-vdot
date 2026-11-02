"""Integrate confirmed frontend evidence into the existing review report.

Preserve original backend prose and original image bytes. Run once from this
workspace; refuse to overwrite a different evidence image or pre-edit backup.
No RTL source, VCD, simulator, reference library, or personal note is modified.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
AUDIT=OUT/'report-extension'
REPORT=ROOT/'reports/stage1/vadd-lifecycle.md'
ASSETS=ROOT/'reports/stage1/assets/vadd'
AUDIT.mkdir(exist_ok=True)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write_json(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def copy_unchanged(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():
        assert sha(src)==sha(dst),f'Preserve existing different file: {dst}'
    else:
        shutil.copy2(src,dst)
    assert sha(src)==sha(dst)

before=REPORT.read_text(encoding='utf-8-sig')
assert '### 3.1 译码' in before and '### 3.1 前端取指' not in before
copy_unchanged(REPORT,AUDIT/'before'/'vadd-lifecycle.md')
old_images=re.findall(r'!\[[^\]]*\]\((assets/vadd/[^)]+)\)',before)
assert len(old_images)==10
old_hashes={x:sha(REPORT.parent/x) for x in old_images}

new_sources=[
    ('C:/Users/Lenovo/AppData/Local/Temp/codex-clipboard-1dc51997-2fc0-4461-ab49-8b591ecb6c3e.png','user-ibuffer-5087ps.png',5087,'IBuffer output and CtrlBlock input identify target; frontend ready=1 while DecodeStage ready=0'),
    ('C:/Users/Lenovo/AppData/Local/Temp/codex-clipboard-33c6a3c5-4390-4545-afee-0e478679ccca.png','user-decode-buffer-5093ps.png',5093,'User red boxes mark successive earlier intervals; only buffer lane 0 valid at Marker'),
    ('C:/Users/Lenovo/AppData/Local/Temp/codex-clipboard-274f5167-bae4-4c7b-8803-8e62085bf360.png','user-decode-accept-5111ps.png',5111,'Target valid/ready before the 5112 ps edge; buffer valid clearing is supported by raw VCD samples'),
]
new_confirmation=[]
for src,name,time,note in new_sources:
    src=Path(src);dst=OUT/name
    copy_unchanged(src,dst)
    new_confirmation.append(dict(source_image=str(src),archived_image=str(dst.relative_to(ROOT)),
        marker_ps=time,sha256=sha(src),evidence_boundary=note))
write_json(OUT/'decode-bridge-user-confirmation.json',dict(
    date='2026-10-19',user_confirmed_edges={'buffer_slot3':5088,'buffer_slot1':5090,'buffer_slot0':5092,'decode_accept':5112},
    clarified_valid_signal='decodeBufValid_0 clears at 5112; io_in_0_valid can remain 1 for the next instruction',
    images=new_confirmation))

front_specs=[
    ('user-ftq-marker5080ps.png','frontend-ftq-marker5080ps.png',5080,'FTQ request edge; Marker shows next entry 0/4'),
    ('user-icache-5083ps.png','frontend-icache-5083ps.png',5083,'ICache response and IFU F2; full data slice from archived sampling'),
    ('user-ifu-5085ps.png','frontend-ifu-5085ps.png',5085,'IFU output before 5086 ps IBuffer acceptance'),
    ('user-ibuffer-5087ps.png','frontend-ibuffer-5087ps.png',5087,'IBuffer to backend input, distinct from DecodeStage acceptance'),
    ('user-decode-buffer-5093ps.png','frontend-decode-buffer-5093ps.png',5093,'Successive buffer slots; user annotations preserved'),
    ('user-decode-accept-5111ps.png','frontend-decode-accept-5111ps.png',5111,'Pre-edge decode identity and valid/ready'),
]
front_images=[]
for source,name,time,note in front_specs:
    src=OUT/source;dst=ASSETS/name
    copy_unchanged(src,dst)
    front_images.append(dict(source=str(src.relative_to(ROOT)),report_image='assets/vadd/'+name,
        marker_ps=time,sha256=sha(dst),caption_scope=note,unchanged=True))
write_json(OUT/'report-images.json',dict(original_images=old_hashes,frontend_images=front_images,
    count=16,scope='Six unmodified frontend screenshots added; original ten images retained'))

# Renumber only the original figure labels and backend subsection headings.
s=re.sub(r'图(\s*)(\d+)',lambda m:'图'+m[1]+str(int(m[2])+6 if int(m[2])>=2 else 1),before)
s=re.sub(r'^(### 3\.)([1-7])(\s)',lambda m:m[1]+str(int(m[2])+1)+m[3],s,flags=re.M)
s=s.replace('分析它从译码、重命名、派发和发射，到执行、物理写回与退休的过程。',
    '分析它从FTQ取指请求、ICache应答、IFU与IBuffer送指，到译码、重命名、派发和发射，再到执行、物理写回与退休的过程。',1)
s=s.replace('PC用于定位静态指令，进入后端后结合ROB标识和物理寄存器编号追踪这次动态执行。',
    'PC用于定位静态指令；前端结合FTQ指针与块内偏移，进入后端分配ROB及物理目的后，再沿这些标识追踪同一次动态执行。同一PC可能重复取回，不能只按最早出现的PC拼接路径。',1)
s=s.replace('| ROB |', '| 前端FTQ / 块内偏移 | `flag=0, value=3`，记为`0/3`；目标`ftqOffset=0xA` |\n| ROB |',1)
s=s.replace('ROB提交则依据`isCommit && commitValid`。',
    'ICache应答采用Valid接口，结合有效应答、地址及IFU的F2推进条件观察；ROB提交依据`isCommit && commitValid`。',1)
timeline='''| 5079 ps | **5080 ps** | FTQ `0/3`取指请求被接受，起点为0x80000134 |
| 5083 ps | **5084 ps** | ICache应答有效，data[95:64]含目标指令；IFU F2推进 |
| 5085 ps | **5086 ps** | IFU位置10的目标被IBuffer接口接受 |
| 5087 ps | **5088 ps** | IBuffer输出槽5由后端入口接收，目标保存到decodeBuf槽3 |
| 5089 / 5091 ps | **5090 / 5092 ps** | 目标在decodeBuf中先移到槽1，再移到槽0 |
| 5093 ps | — | 缓冲槽0与译码输入有效，译码ready=0，继续等待 |
'''
s=s.replace('| 5111 ps | 5112 ps | 译码接口接收目标指令 |',timeline+'| 5111 ps | **5112 ps** | 译码接受目标；decodeBufValid_0清零，入口转向后续指令 |',1)
front=(OUT/'frontend-section.md').read_text(encoding='utf-8')
s=s.replace('### 3.2 译码',front+'\n### 3.2 译码',1)
s=s.replace('通过该实例，可以从程序行为追踪到处理器内部的译码、数据依赖、调度和提交过程，为后续指令设计提供源码与波形分析基础。',
    '前端以FTQ `0/3`和块内偏移`0xA`关联目标，后端以ROB `1/0x10`及向量物理目的`0x33`继续追踪。5088 ps的后端入口接收、5112 ps的译码接收、5272 ps的物理写入、5274 ps的退休及5278 ps的提交映射更新各有对应证据，组成从取指请求到提交结果的观察路径。\n\n本次前端分析始于FTQ取指请求，未展开BPU预测算法、ICache缺失/补行及地址转换内部过程；功能验证范围仍为本次e32/m1/VL4无掩码样例。通过该实例，可以从程序行为追踪到取指、译码、数据依赖、调度和提交过程，为后续指令设计提供源码与波形分析基础。',1)
append_b='''### B.1 前端与后端入口

以下层级接在`TOP.SimTop.l_soc.core_with_l2.core`后；源码路径相对本次XiangShan提交的`src/main/scala/xiangshan/`。

| 阶段 | 波形层级与信号 | 源码入口 |
|---|---|---|
| 取指请求 | `frontend.inner_ftq`；`io_toIfu_req_valid/ready`、`bits_startAddr`、`bits_nextStartAddr`、`bits_ftqIdx_flag/value` | `frontend/FrontendBundle.scala:35–43`；`frontend/Frontend.scala:177–188` |
| ICache应答 | `frontend.inner_icache`；`io_fetch_resp_valid`、`bits_vaddr_0`、`bits_doubleline`、`bits_exception_0/1`、`bits_data` | `frontend/icache/ICacheMainPipe.scala:53,537–555` |
| IFU切分与输出 | `frontend.inner_ifu`；`f2_ftq_req_ftqIdx_*`、`f2_fire`、`f2_cut_ptr_10/11`；`io_toIbuffer_*`及位置10字段 | `frontend/IFU.scala:458–507`；`frontend/Frontend.scala:204` |
| IBuffer输出 | `frontend.inner_ibuffer`；`io_out_5_*`、`io_decodeCanAccept`、`io_flush` | `frontend/IBuffer.scala:273–299`；`frontend/Frontend.scala:408–416` |
| 后端入口与缓冲 | `backend.inner_ctrlBlock`；`io_frontend_cfVec_5_*`、`decodeFromFrontendAcceptNum`、`decodeBufValid_n`、`decodeBufBits_n_pc/instr/ftqPtr_*/ftqOffset`，n为3、1、0 | `backend/CtrlBlock.scala:414–502` |
| 译码衔接 | `backend.inner_ctrlBlock.decode`；`io_in_5_valid/ready`、`io_in_0_*`、`io_redirect` | 同上；缓冲与前端输入选择逻辑 |

本次ICache数据位段结论由响应数据和IFU切分指针共同核对，完整数值见附录C的V7。图中SST当前选中模块与已经添加到波形区的其他模块信号可以不同，应按本表归属读取。

### B.2 后端

'''
s=s.replace('波形公共前缀为`TOP.SimTop.l_soc.core_with_l2.core.backend`',append_b+'波形公共前缀为`TOP.SimTop.l_soc.core_with_l2.core.backend`',1)
s=s.replace('[10张截图来源]','[原10张截图来源]',1)
v7='''| V7 | 前端请求、应答与译码衔接 | [FTQ采样](../../artifacts/vadd4-frontend-2026-10-19/ftq-request-observations.json)、[ICache采样](../../artifacts/vadd4-frontend-2026-10-19/icache-response-observations.json)、[数据排列核对](../../artifacts/vadd4-frontend-2026-10-19/icache-data-layout.json)、[入口缓冲逐ps采样](../../artifacts/vadd4-frontend-2026-10-19/decode-bridge-observations.json)、[解析脚本](../../artifacts/vadd4-frontend-2026-10-19/inspect_decode_bridge.py)、[命令与退出码](../../artifacts/vadd4-frontend-2026-10-19/decode-bridge-run.json)、[源码commit/哈希](../../artifacts/vadd4-frontend-2026-10-19/report-source-evidence.json) |
| V8 | 前端图片与文档核验 | [6张图来源及原10图哈希](../../artifacts/vadd4-frontend-2026-10-19/report-images.json)、[入口衔接人工确认](../../artifacts/vadd4-frontend-2026-10-19/decode-bridge-user-confirmation.json)、[文档补充检查](../../artifacts/vadd4-frontend-2026-10-19/report-extension/check-result.json) |
'''
s=s.replace('\n\n参考资料：','\n'+v7+'\n参考资料：',1)

def backend(text,heading):
    return text[text.index(heading):text.index('## 4 实验结论')]
new_backend=backend(s,'### 3.2 译码')
normalized=re.sub(r'^(### 3\.)([2-8])(\s)',lambda m:m[1]+str(int(m[2])-1)+m[3],new_backend,flags=re.M)
normalized=re.sub(r'图(\s*)(\d+)',lambda m:'图'+m[1]+str(int(m[2])-6),normalized)
assert normalized==backend(before,'### 3.1 译码'),'Backend prose changed beyond renumbering'
old_a=before[before.index('## 附录 A'):before.index('## 附录 B')]
new_a=s[s.index('## 附录 A'):s.index('## 附录 B')]
assert old_a==new_a,'Build/run commands changed'
assert all(sha(REPORT.parent/x)==h for x,h in old_hashes.items())
REPORT.write_text(s,encoding='utf-8',newline='\n')
write_json(AUDIT/'extension-result.json',dict(report=str(REPORT.relative_to(ROOT)),
    before_sha256=sha(AUDIT/'before/vadd-lifecycle.md'),after_sha256=sha(REPORT),
    original_backend_preserved_except_numbering=True,build_run_appendix_unchanged=True,
    original_images_unchanged=True,new_frontend_images=len(front_images),total_images=16))
print('Updated report: 6 frontend figures added; original backend prose and 10 image bytes preserved.')
