# 第三阶段报告与收尾索引

更新：2026-10-27。指定NEMU/RTL一致性、标准RVV等价和三类性能测量已有证据；bijzGZ逐轮补证核验完成。三份报告、取证附录、V3稿和交付索引已形成；五组终端图已入文（F02补图已与原PASS/退出码图配套核验），V3成片未完成，G3不计整阶段通过。

2026-10-29 新增已授权补测：[分段长点积](segmented-dot.md)已完成本地正确性预检，服务器待执行。三条路径在G=8/16下比较寄存器归约与相同输出的中间物化对照；只构建新应用，复用原核心和参考库。[命令与回传](../../artifacts/vdot-segment-2026-10-29/README.md)。旧报告实测值保持，新增性能尚未取得。

## 1 报告入口

| 材料 | 对应要求 | 内容 |
|---|---|---|
| [NEMU与DiffTest](difftest.md) | C3.1.1/C3.1.2 | 参考模型接入、ABI范围、分层测试、mtval失败与修复回归 |
| [标准RVV等价](rvv-equivalence.md) | C3.2 | 两种基线、144例/432调用、完整输出与约定状态 |
| [分层性能](performance.md) | C3.3 | 计时预检、依赖链、八路批处理、预热小数组 |
| [逐轮与计数器附录](performance-evidence.md) | C3.3证据 | bijzGZ正式30样本、10个预热周期、阶段耗时、37条全程计数 |
| [交付与复现索引](delivery.md) | 第三阶段材料 | 源码/补丁/配置/身份/证据路径及未完成项 |
| [V3录屏稿和取图表](../../recording/stage3/README.md) | V3 | 约7～9分钟演示建议、日志入口、波形与性能图、成片检查 |

## 2 已取得的工程证据

| 项目 | 已有结论 | 证据入口 |
|---|---|---|
| NEMU扩展 | 真实库API268例通过；另10例配置不适用，不计通过 | [API结果](../../artifacts/vdot-integration-2026-10-24/nemu-api-151012/result.json) |
| RTL/NEMU一致性 | 异常64、重叠60、smoke7及Hello/VADD通过；120例依赖/混发/分支异常CSR通过 | [mtval回归](../../artifacts/vdot-mtval-fix-2026-10-24/server-xYGYlZ/review.json)、[120例](../../artifacts/vdot-pipeline-2026-10-24/server-JuGUz6/review.json) |
| 标准RVV等价 | 两基线144例/432调用；完整结果、指定状态、DiffTest/GOOD TRAP/退出0 | [8nvimb](../../artifacts/vdot-rvv-equivalence-2026-10-26/server-8nvimb/review.json) |
| 计时预检 | 42调用/6预热/36正式，六种退休增量符合预期 | [5vHUp8](../../artifacts/vdot-timing-pilot-2026-10-26/server-5vHUp8/review.json) |
| 完整操作依赖链 | 新增操作VDot7、m1为55、mf2为47周期；mf2/VDot增量比6.71 | [KiI3xX](../../artifacts/vdot-chain-2026-10-26/server-KiI3xX/review.json) |
| 八路寄存器批处理 | VDot两段增量1周期，mf2约3；N128 mf2/VDot区间比2.40 | [uLgHm6](../../artifacts/vdot-throughput-2026-10-26/server-uLgHm6/review.json) |
| 预热小数组 | N128 VDot2239、mf2为2241周期，区间比1.0009，基本持平 | [bijzGZ](../../artifacts/vdot-e2e-2026-10-27/server-bijzGZ/review.json) |

四个计时应用均通过显式源码NEMU DiffTest、GOOD TRAP及对应退出码检查；预检重试未单独记录tee退出码，不补造。依赖链/八路/小数组每点3个正式样本，预检每点6个。波形证明的单例取消、CSR请求、发射前端口竞争范围见[NEMU与差分报告](difftest.md)及第二阶段功能报告。

## 3 本次补证与材料核对

[原始回传](../../artifacts/stage3-closeout-2026-10-27/e2e-read/user-read-output.txt)和[核验](../../artifacts/stage3-closeout-2026-10-27/e2e-read/review.json)：30正式样本的顺序、instret、consumer全部符合矩阵，10组统计一致；构建3.525秒、整核运行1651.336秒。37条PERF记录覆盖22个所选名称，缺失清单为空，但范围为整个应用，未确定小数组瓶颈。

只读回传核对的是保存身份，未重算远端当前二进制哈希。开头命令回显有乱码，完整结果行已校验；不执行粘贴代码、不重跑成功仿真。后续MIwNSR包已在本地核验并解包，四组162调用（36预热/126正式）原日志/JSON/CSV一致，36组统计复算一致；预热全部字段已补齐，见[归档状态](../archive-status.md)。

选定的30项源码/补丁身份与既有manifest匹配，五个应用包的15个源文件及5个矩阵与工作区保存内容逐字一致；[60项文件清单](../../artifacts/stage3-closeout-2026-10-27/source-inventory.json)仅覆盖本轮交付对象，不是全库或最终包验收。[开发过程总录](../../docs/development-history.md)第20.3节记录本次修改、方法和构建运行关系。

## 4 当前待办

1. MIwNSR和LpAu2Y均已本地核验解包，不重复下载、打包或仿真；第一阶段VADD及已有端口竞争VCD继续保留。
2. 13张用户日志图已保存并核对，原12张接受、F02原局部图现已由补图配齐；主要图已嵌入第二/三阶段报告。[逐图记录](../../artifacts/report-screenshots-2026-10-27/README.md)。
3. 第二阶段代表波形及F07失败对照、第三阶段F02校准补图均已入文。[最后补图核对](../../artifacts/material-readiness-2026-10-27/README.md)。下一步报告终稿、V1/V2/V3、候选包和平台提交检查，详见[整体缺口](../../docs/submission-review-2026-10-27.md#0-补图完成后的实际缺口与优先级)；G3仍需V3与最终材料，不默认追加实验。
