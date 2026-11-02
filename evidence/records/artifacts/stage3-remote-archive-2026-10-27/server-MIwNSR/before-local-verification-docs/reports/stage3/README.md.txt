# 第三阶段报告与收尾索引

更新：2026-10-27。指定NEMU/RTL一致性、标准RVV等价和三类性能测量已有证据；bijzGZ逐轮补证核验完成。三份报告、取证附录、V3稿和交付索引已形成；终端截图与V3成片未完成，G3不计整阶段通过。

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

只读回传核对的是保存身份，未重算远端当前二进制哈希。开头命令回显有乱码，完整结果行已校验；不执行粘贴代码、不重跑成功仿真。原始samples.json/result.json/architecture.log仍在服务器。预热回传仅提供周期，本地不补造其他原始字段。

选定的30项源码/补丁身份与既有manifest匹配，五个应用包的15个源文件及5个矩阵与工作区保存内容逐字一致；[60项文件清单](../../artifacts/stage3-closeout-2026-10-27/source-inventory.json)仅覆盖本轮交付对象，不是全库或最终包验收。[开发过程总录](../../docs/development-history.md)第20.3节记录本次修改、方法和构建运行关系。

## 4 当前待办

1. 先执行[完整日志归档命令](../../artifacts/stage3-remote-archive-2026-10-27/README.md)，收集五个第三阶段主运行目录及五个差分/构建/失败追溯目录。MIwNSR回传显示远端已归档10目录/264文件，collector/tee/script均0；[本地接收目录与下载清单](../../artifacts/stage3-remote-archive-2026-10-27/server-MIwNSR/README.md)已准备，下载及校验尚未完成，不要重复执行归档命令。
2. 下载并核对归档包、文件清单和SHA256，再补齐本地原始证据。归档只收集现存文件，不重跑仿真。
3. 用户后续统一截S3-F01/F02/F03a/F04a/F05a并录制V3。既有[取图表和录屏稿](../../recording/stage3/README.md)继续使用；待视频回放、图像归档和最终包核验完成后判断G3。

不默认启动额外性能实验。6.71、2.40、1.0009属于不同接口，不能合并为通用加速倍数，也不能跨组相减求纯访存开销。v0.1中的A01～A09、配置适用性和未覆盖范围继续保留。提交与外发未执行。
