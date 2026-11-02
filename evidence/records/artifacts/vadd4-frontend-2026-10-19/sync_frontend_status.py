"""Update the current documentation state after the confirmed frontend trace."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'report-extension'
changed=[]
def edit(name,fn):
    p=ROOT/name
    old=p.read_text(encoding='utf-8-sig')
    new=fn(old)
    if old==new:return
    backup=OUT/'before'/name
    backup.parent.mkdir(parents=True,exist_ok=True)
    assert not backup.exists(),f'Existing backup preserved: {backup}'
    shutil.copy2(p,backup)
    p.write_text(new,encoding='utf-8',newline='\n')
    changed.append({'file':name,'before_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})

def report(s):
    s=s.replace('\n\n| V7 |','\n| V7 |')
    note='本表的块内偏移指IBuffer/译码携带的目标半字位置；FTQ请求中同名的ftqOffset描述预测跳转位置，不能将两者混用。\n\n'
    s=s.replace('VCD时间单位为1 ps',note+'VCD时间单位为1 ps',1)
    s=s.replace('参考资料：','参考资料：[香山IFU说明](https://docs.xiangshan.cc/projects/design/zh-cn/kunminghu-v2/frontend/IFU/)（原理参考，具体接口以本次源码为准）、',1)
    return s
edit('reports/stage1/vadd-lifecycle.md',report)

def progress(s):
    s=re.sub(r'^更新：[^\n]*',
      '更新：2026-10-19。用户已确认前端到译码的剩余波形，[VADD报告](reports/stage1/vadd-lifecycle.md)已加入FTQ请求、ICache应答、IFU、IBuffer与decodeBuf到5112ps译码接收的分析。正文新增6图，共16图；原后端分析及原10图保留。图注区分Marker与事件沿，原始采样/截图来源见前端归档。未重建或重跑RTL。',s,count=1,flags=re.M)
    s=s.replace('VADD正文保留10图','VADD正文16图（原10图及新增6图）')
    s=s.replace('10图均在正文，沿同一动态指令分析','16图均在正文，按FTQ身份接到ROB身份，沿同一动态指令分析')
    s=s.replace('A标准评审结构，10图全留正文','A标准评审结构，保留原10图并加入6张已确认前端图')
    row='| VADD前端到译码 | 用户确认FTQ/ICache/IFU/IBuffer与decodeBuf槽3→1→0，5112ps译码接收；6图和原VCD样本一致 | 已补入报告；接下来审阅及准备录屏，不要求重做实验 |\n'
    s=s.replace('| VADD译码 |',row+'| VADD译码 |',1)
    return s
edit('PROGRESS.md',progress)

def handoff(s):
    s=re.sub(r'^更新：\*\*2026-10-19（Asia/Shanghai）\*\*。[^\n]*',
      '更新：**2026-10-19（Asia/Shanghai）**。用户已确认FTQ取指请求、ICache应答、IFU输出及IBuffer→decodeBuf→5112ps译码接收；前端已补入[VADD评审报告](../reports/stage1/vadd-lifecycle.md)第3.1节、时间线及附录。新增6张原样截图，共16图，原后端分析只调整小节/图号，原10图及构建运行命令保留。采样、人工确认、源码哈希和文档检查见[前端归档](../artifacts/vadd4-frontend-2026-10-19/)。未运行新RTL仿真，下一步是报告审阅、录屏与材料预检。平台简述仍在环境报告，正式vdot工作另行推进。',s,count=1,flags=re.M)
    s=re.sub(r'^用户已完成Hello和VADD后端观察；[^\n]*',
      '用户已完成Hello及VADD从FTQ请求到提交的本人观察，当前接续报告审阅、录屏及材料预检。IBuffer输出接收与译码接收是两个边界；5112ps清零的是decodeBufValid_0，io_in_0_valid仍可表示后续指令。FTQ请求的ftqOffset为预测跳转位置，与IBuffer/译码的目标offset不同。',s,count=1,flags=re.M)
    s=s.replace('VADD从译码到物理写入、ROB退休、已提交映射已核验；10张原图、25组检查点和执行过程文档已形成',
      'VADD从FTQ取指请求到已提交映射已核验；16图保留正文，原后端25组检查点及新增前端采样均有索引')
    s=s.replace('A标准评审结构；VADD10图全在正文','A标准评审结构；保留原10图，新增6张前端图，全在正文')
    s=s.replace('VADD正文保留10图','VADD正文16图（保留原10图）')
    anchor='| 5111 / 5112 ps |'
    if '| 5079 / 5080 ps |' not in s:
      s=s.replace(anchor,
       '| 5079 / 5080 ps | FTQ0/3请求，startAddr80000134；沿后切换0/4；截图Marker=5080 |\n'
       '| 5083 / 5084 ps | ICache应答，data[95:64]=021101d7；IFU F2的FTQ0/3且fire1 |\n'
       '| 5085 / 5086 ps | IFU位置10目标、valid=ready1、掩码D555且IBuffer flush0 / 接受 |\n'
       '| 5087 / 5088 ps | IBuffer槽5，后端cfVec5 ready1而decode.in5.ready0 / 保存到decodeBuf3 |\n'
       '| 5089 / 5090、5091 / 5092 ps | 目标移至decodeBuf1，再移至0；保持FTQ0/3、offsetA |\n'+anchor,1)
    return s
edit('docs/HANDOFF.md',handoff)

def verification(s):
    s=re.sub(r'^更新日期：2026-10-19。[^\n]*',
      '更新日期：2026-10-19。前端到译码的本人观察已确认，已将6张前端截图、时间点及信号说明加入VADD评审报告，保留原后端内容和10图。以下区分历史采样、本轮文档核验与用户确认；未新增构建或RTL仿真。',s,count=1,flags=re.M)
    s=s.replace('## 2026-10-19 前端IFU、FTQ本人确认与ICache应答抽查','## 2026-10-19 前端到译码确认与报告补充',1)
    s=s.replace('下一步确认ICache响应及后端入口衔接。保持报告原10张图与正文，待前端链路确认后统一补入。',
      'ICache与入口衔接已在后续本人观察中确认，现一并补入报告；原采样文件保留其采样时的状态说明。')
    s=s.replace('用户本段尚未本人确认，不提前改写执行报告。',
      '用户随后确认该段，提供5087ps入口、5093ps缓冲移动和5111ps接受沿前截图；[原图来源及人工确认](../artifacts/vadd4-frontend-2026-10-19/decode-bridge-user-confirmation.json)区分图中实际Marker和事件时刻。')
    heading='## 2026-10-19 第一阶段报告评审版修订'
    insert='''本次按已确认波形扩展[VADD报告](../reports/stage1/vadd-lifecycle.md)：前端小节、完整时间表、前端FTQ身份、接口字段/源码表、证据索引和结论已补齐。6张前端图原样复制进报告assets；原10图逐一校验哈希，原后端正文除小节/图号外逐字保持，构建运行附录保持不变。[图片清单](../artifacts/vadd4-frontend-2026-10-19/report-images.json)、[源码HEAD/相关diff/哈希](../artifacts/vadd4-frontend-2026-10-19/report-source-evidence.json)、[扩展结果](../artifacts/vadd4-frontend-2026-10-19/report-extension/extension-result.json)、[最终文档检查](../artifacts/vadd4-frontend-2026-10-19/report-extension/check-result.json)。修改前报告及受影响文档保存在同目录before；检查脚本和实际运行记录也在该目录。

图2的Marker为5080ps，不能标成5079ps截图；图3数据总线被截断，[95:64]据原VCD及用户确认；图6红框是用户原图自带，显示不同时间段的槽位；图7为5111ps沿前，5112ps清零的是decodeBufValid_0而非所有valid。报告正文共16图，均在附录前。此工作包只整理既有波形证据，不是重新运行芯片仿真或新增性能测试。

'''
    assert heading in s
    return s.replace(heading,insert+heading,1)
edit('docs/verification.md',verification)
edit('README.md',lambda s:s.replace('VADD10张截图全部保留正文','VADD已补前端取指到译码，原10张图与新增6张图均保留正文'))
edit('docs/requirements_matrix.md',lambda s:s.replace('实验与用户观察完成；10图全保留正文，图注统一，命令与证据在附录',
    '实验与用户观察完成；已补FTQ取指到译码，16图在正文且保留原后端分析，命令与证据在附录'))
edit('docs/stage1-remaining-checklist.md',lambda s:s.replace('10张VADD截图全留正文','原10张VADD截图与新增6张前端截图全留正文').replace('同一条指令从译码到提交的证据','同一条指令从FTQ取指请求到提交的证据'))
edit('docs/learning_path.md',lambda s:s.replace('更新：2026-10-18。你已完成Hello、标量ADD学习，并亲自追踪四元素VADD到物理写入、ROB提交与映射更新；',
    '更新：2026-10-19。你已完成Hello、标量ADD学习，并亲自追踪四元素VADD从FTQ取指请求、入口缓冲到译码、物理写入、ROB提交与映射更新；',1))
edit('exercises/vadd4/README.md',lambda s:s.replace('同一镜像已导出VCD，完整生命周期文档已形成；正式平台核验、定制Hello、环境报告和视频仍未完成。',
    '同一镜像的VCD已完成FTQ取指到提交的观察并写入执行报告；定制Hello及两份评审稿已形成，录屏和材料预检待完成。正式vdot合同与源码NEMU另按看板推进。'))

def wave(s):
    s=s.replace('# VADD波形操作指引：译码到提交','# VADD波形操作指引：取指到提交',1)
    s=re.sub(r'^2026-10-18状态：[^\n]*',
      '2026-10-19状态：用户已完成FTQ取指、ICache应答、IFU/IBuffer、入口缓冲到译码的补看，连同原后端路径已写入[执行过程报告](../../reports/stage1/vadd-lifecycle.md)，正文共16图。第六小节保留前端复查入口；无需重新导波形。',s,count=1,flags=re.M)
    s+='''
## 第六小节：前端取指到译码的复查入口（2026-10-19已确认）

本节各路径相对`TOP.SimTop.l_soc.core_with_l2.core`。保持clock/reset，窗口5074～5116ps；目标PC80000148、机器码021101d7。前端身份为FTQ0/3、IBuffer/译码中的offsetA，进入后端分配ROB后再跟踪ROB1/10及向量pdest33。

| 观察点 | 选择scope与字段 | 已确认结果 |
|---|---|---|
| 5079ps → 5080ps | frontend.inner_ftq；io_toIfu_req的valid/ready、startAddr、nextStartAddr、ftqIdx | 1/1、80000134、80000154、0/3；沿后接口转0/4 |
| 5083ps | frontend.inner_icache；io_fetch_resp的valid、vaddr_0、doubleline、exception_0/1、data | 1、80000134、1、0/0；512位data[95:64]=021101d7 |
| 5083ps | frontend.inner_ifu；f2_ftq_req_ftqIdx_flag/value、f2_fire | 0/3、1；返回数据按bank排列，不能从最低位起按20字节请求偏移截取 |
| 5085ps → 5086ps | frontend.inner_ifu；io_toIbuffer的valid/ready、pc_10、instrs_10、valid/enqEnable掩码、ftqPtr；另看IBuffer flush | 1/1、目标PC/字、D555/D555、0/3、flush0 |
| 5087ps → 5088ps | frontend.inner_ibuffer.io_out_5；backend.inner_ctrlBlock.io_frontend_cfVec_5；decode.io_in_5 | 同一目标；后端入口valid=ready1而译码ready0，沿后保存进decodeBuf3 |
| 5089/5091/5093ps | backend.inner_ctrlBlock的decodeBufValid_n、decodeBufBits_n_pc/instr，n=3/1/0 | 目标先后占三个槽，FTQ身份/offset保持不变；前面指令接受后剩余项向前排列 |
| 5111ps → 5112ps | backend.inner_ctrlBlock.decode.io_in_0及io_redirect；CtrlBlock.decodeBufValid_0 | 沿前目标valid=ready1、redirect0；沿后缓冲valid0，译码入口转PC8000014c |

原始29个入口衔接样本及完整命令见[前端归档](../../artifacts/vadd4-frontend-2026-10-19/)。截图/解释以[报告第3.1节](../../reports/stage1/vadd-lifecycle.md)为准。5112ps缓冲数据可以保留旧值，必须结合decodeBufValid判断有效性；译码入口valid可因下一条指令仍为1。
'''
    return s
edit('exercises/vadd4/WAVE.md',wave)
(OUT/'document-changes.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Synchronized {len(changed)} affected Markdown files; no source changes or simulation.')
