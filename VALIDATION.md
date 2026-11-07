# 源码、工具与材料核对

2026-11-02将作品目录改为完整源码交付，配套源码、运行工具与技术报告。11月2日检查覆盖源码准备、构建入口、辅助工具与材料；11月3日新增Docker整核构建及17个应用的实际复现，记录见下文。

## 完整源码与应用

从锁定Git对象导出XiangShan、NEMU、nexus-am及构建依赖，共21个版本固定的源码目录，再应用既有正式补丁。19个实现文件与已验证快照一致。Windows可移植目录的权限、符号链接和文件身份由[source-tree.json](configs/source-tree.json)登记；原始补丁与基线仍保留。

在新的Linux临时仓库中实际执行`tools/prepare_sources.py`，逐项检查4750个源码/构建信息条目、23个符号链接、执行权限及17个应用复制。检查通过，已有目标目录会被拒绝，不创建嵌套Git仓库。[完整准备检查](evidence/package-checks/full-source-preparation.json)

应用的原始版本依据继续保留：[应用源码核对](evidence/package-checks/app-source-check.json)、[实现文件检查记录](configs/source-snapshots.json)、[既有补丁恢复记录](evidence/package-checks/patch-validation.json)。NEMU配置和16字节启动Flash与已保存成功版本一致。

## 构建入口与运行工具

在上述无嵌套Git的目录执行`mill -i show xiangshan.resources`，退出0；Mill构建定义能够加载，DiffTest的124个资源文件按保存清单正确枚举。[检查参数与退出状态](evidence/package-checks/mill-resources-check.json)

轻量工具检查使用合成日志和小型模拟进程，覆盖成功、失败、超时、Ctrl+C、已有目录保护和Bash语法。新增单用例入口检查包括Hello参数与路径、dry-run不执行、指定运行目录读取、错误用例拒绝、异常退出状态显示。完整源码准备检查中的14项流程检查包含这些步骤，以及原有15项辅助检查；这不代表重新运行硬件。[流程记录](evidence/package-checks/full-source-preparation.json)

## 2026-11-03 环境与应用编译先行检查

在Docker Desktop中构建环境镜像，并在独立Linux数据卷内从提交材料准备源码。环境检查、NEMU以及Hello/VADD/VDot-smoke应用编译均通过，NEMU参考库的动态加载与必要导出符号检查通过。此次没有编译整核emu或运行DiffTest仿真。

实测发现并修复了Verilator缺少`libfl-dev`、首次NEMU构建缺少配置生成步骤的问题。NEMU配置同步前后内容一致。软件包版本、原始构建日志与检查结果见[容器验证摘要](evidence/package-checks/docker-20261103/summary.json)及[复现环境说明](environment/README.md)。

## 2026-11-03 本机整核与验收流程实测

在独立Linux数据卷内，从本仓库源码构建NEMU参考库和整核emu。构建配置为单核MinimalConfig、EMU_TRACE=1、NO_DIFF=0、JVM_XMX=6G、2路编译。本轮补齐GNU time与SQLite开发库后增量续建，保留已生成的RTL、C++及日志，最终构建退出0；没有复用历史emu二进制。

| 组别 | 实际结果 | 原始验收记录 |
|---|---|---|
| 基础 | 3/3通过 | [acceptance.json](evidence/package-checks/fullcore-local-20261103/runs/smoke-fd0f09e2f8db4b869aaee0a033c12da1/acceptance.json) |
| 完整功能 | 10/10通过 | [acceptance.json](evidence/package-checks/fullcore-local-20261103/runs/functional-15d1110f8ae94c2ab9c9023b8856f762/acceptance.json) |
| 性能 | 7/7通过 | [acceptance.json](evidence/package-checks/fullcore-local-20261103/runs/performance-42571a4f4b0e46a3b63635ab4eb26b93/acceptance.json) |

三组共20次仿真，覆盖17个不同应用，包含功能组对基础3项的重复运行。每项均从原始日志核对应用标志、DiffTest、参考库路径、GOOD TRAP与退出状态。性能数值保留在本次run.log中，报告中的历史测量表未被替换。[完整摘要及耗时](evidence/package-checks/fullcore-local-20261103/summary.json)

独立新副本实测通过容器初始化、环境检查、状态查询、命令执行与结果导出。辅助工具10项单元测试通过；模拟低磁盘条件的实际容器停止测试通过，退出75，未填满磁盘。[入口检查](evidence/package-checks/fullcore-local-20261103/controller-workflow.json)、[单元测试](evidence/package-checks/fullcore-local-20261103/helper-tests.log)、[空间保护测试](evidence/package-checks/fullcore-local-20261103/watchdog-test.json)

实际安装版本、构建及仿真原始日志均保存在本次证据目录。

## 波形还原

三份历史VCD均完成压缩、还原与完整性检查。又在新Linux目录使用仓库的`prepare_recording.py`实际还原三份VCD，验证VADD分卷连续读取，随后检查Windows GTKWave的WSL路径转换。[波形还原检查](evidence/package-checks/wave-restore-check.json)

## 2026-11-03 VDot-smoke 单条命令与清单修复

`recording_case.py`新增`vdot-smoke`入口，支持输入检查、正式运行和按指定目录回看结果。正式运行结束后直接显示七例PASS、DiffTest、GOOD TRAP和退出状态，并保留原有ANSI颜色清理。通过`container.py exec`实际运行七例全部通过，用时约64秒；同一目录的结果回看通过，Hello/VADD输入检查也通过。[实测记录](evidence/package-checks/vdot-smoke-entry-20261103/summary.json)

清单枚举在进入目录前排除Metals、Scala CLI、Bloop、BSP和Mill输出等本地缓存，同时继续校验所有4750个声明的源码条目。五项针对性检查通过，覆盖缓存排除、正常源码保留、逐例显示、错误用例拒绝和失败状态显示。宿主机和Linux工作区分别校验通过后同步会话清单；已有仿真器、参考库、应用镜像和运行记录保留，未重编整核。[检查日志](evidence/package-checks/vdot-smoke-entry-20261103/helper-tests.log)

## 2026-11-05 录屏文件检查

3份成片已完成全长音视频解码，退出码均为0；每份视频抽查6处画面，均能显示对应源码、报告、运行结果或波形。视频均为1920×1080、30帧/秒，包含H.264视频与AAC音轨。文件名和时长见[视频目录](videos/README.md)。本次检查覆盖文件解码与画面抽样，未逐句审听全部讲解。[检查记录与原始解码日志](evidence/package-checks/delivery-20261105/summary.json)

视频目录保留3份成片和观看说明，文件通过Git LFS管理。原始检查日志仍按测试日期归档。

## 材料入口

各项检查的参数、输出和退出状态保存在上述原始记录中。复现操作见[复现指南](REPRODUCE.md)，实验材料见[证据索引](evidence/index.md)，成片状态见[视频入口](videos/README.md)。

