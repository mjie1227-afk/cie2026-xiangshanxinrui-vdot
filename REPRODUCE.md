# 编译与复现指南

本仓库包含已应用VDot修改的XiangShan、NEMU、nexus-am和17个测试应用。按下列步骤可在Docker Linux环境中，从源码完成编译、功能验证和性能测试。已有实测结果及原始日志见[验证记录](VALIDATION.md)。

三阶段演示视频由Git LFS随仓库管理，克隆后运行 `git lfs pull` 和 `python tools/verify_videos.py` 获取并校验，详见[视频索引](videos/README.md)。下面的编译和测试流程不依赖视频文件。

## 1 准备环境

下载并解压完整源码包，或克隆对应提交版本，进入包含`README.md`、`src/`、`apps/`和`tools/`的仓库根目录。后续命令均在该目录执行。

- **系统与软件**：x86_64 Windows使用Docker Desktop的Linux容器模式（WSL2后端）；x86_64 Linux使用Docker Engine。宿主机安装Python 3.9或更新版本。
- **资源**：建议为Docker分配至少16 GiB内存；默认使用2路编译，内存较小时需保留交换空间。Docker存储盘至少预留50 GiB，源码所在盘至少预留3 GiB；Windows系统盘至少预留12 GiB。首次整核编译按小时级预留时间。
- **网络**：首次搭建和编译需要联网，脚本会从Docker Hub、Ubuntu软件源、GitHub和Maven Central下载环境及Scala/Chisel依赖，之后可复用缓存。仓库提供环境构建配置，工具链由脚本安装，无需在宿主机逐个配置。

打开Docker，等待引擎启动。在**Windows PowerShell、仓库根目录**依次执行：

```powershell
python --version
docker info
python tools/host_storage.py
```

Linux Bash使用相同命令，将`python`替换为`python3`即可。后文沿用Windows写法。

Docker应显示Server信息，空间检查应显示`HOST_STORAGE_OK`。Windows上的Docker数据盘与源码目录可能不在同一块磁盘，可在Docker Desktop的`Settings → Resources → Advanced → Disk image location`查看或调整。若脚本无法识别存储位置，将`VDOT_DOCKER_STORAGE_PATH`设为实际目录后重试。

## 2 建立编译环境

先构建环境镜像：

```powershell
python tools/container.py image
```

镜像包含JDK 21、Mill 0.12.3、Verilator 5.052、Clang 19、RISC-V GCC 12和所需开发库。成功显示`CONTAINER_EXIT_CODE=0`。

再初始化Linux工作目录，**每份新仓库仅执行一次**：

```powershell
python tools/container.py init
```

脚本自动检查仓库文件，将源码复制到独立的Docker Linux数据卷，后续编译和仿真均在该工作目录中进行。成功显示`CONTAINER_INIT_OK`和`CONTAINER_EXIT_CODE=0`。工作目录位置保存在宿主机的`work/container-session.json`，后续命令会自动读取。

## 3 检查工具链

```powershell
python tools/container.py check
```

首次运行会从仓库源码准备`work/build/`，恢复所需权限、符号链接、NEMU配置和测试应用。随后检查工具版本，并实际完成Java、C/C++、RVV汇编和小型Verilator模型的编译运行。

成功标志为：

```text
SOURCE_PREPARE_OK ...        # 首次准备源码时出现
ENV_CHECK=PASS
REPRODUCE_STAGE=check PASS
CONTAINER_EXIT_CODE=0
```

## 4 编译NEMU与整核仿真器

```powershell
python tools/container.py build
```

脚本依次编译NEMU参考库和香山整核仿真器emu，首次编译会获取Scala/Chisel依赖。整核配置为单核`MinimalConfig`，使用`EMU_TRACE=1`、`NO_DIFF=0`、`JVM_XMX=6G`及默认2路编译。

两项构建均应显示`BUILD_EXIT_CODE=0`，最终显示`REPRODUCE_STAGE=build PASS`和`CONTAINER_EXIT_CODE=0`。生成文件位于容器的Linux工作目录：

```text
work/build/NEMU/build/riscv64-nemu-interpreter-so
work/build/XiangShan/build/emu
```

构建期间可在另一个同目录终端查看最新进度：

```powershell
python tools/container.py log
```

## 5 基础测试

```powershell
python tools/container.py smoke
```

依次编译并运行Hello、VADD和VDot-smoke，连接本次构建的NEMU参考库进行DiffTest。应用使用`ARCH=riscv64-xs`、`MARCH=rv64gcv`。

| 应用 | 预期输出 |
|---|---|
| Hello | `hello xiangshan, I am Meijie`及源码中设定的打印内容 |
| VADD | `PASS: vadd.vv produced [11, 22, 33, 44]` |
| VDot-smoke | `PASS VDOT_SMOKE cases=7` |

脚本还会检查DiffTest启用、`HIT GOOD TRAP`和进程退出状态。三项全部通过后显示`SUITE_PASS smoke 3/3`及`REPRODUCE_STAGE=smoke PASS`。

## 6 完整功能测试

```powershell
python tools/container.py functional
```

运行10个应用，包含基础3项，以及异常、寄存器重叠、依赖链、混合指令、取消与CSR、端口竞争候选测试和标准RVV等价测试。

主要检查包括VDot基础7例、异常64例、重叠60例、依赖48例、混合32例、取消与CSR 40例，以及RVV等价144组输入、432次内核调用。端口竞争候选测试的分析见技术报告。

全部通过后显示`SUITE_PASS functional 10/10`及`REPRODUCE_STAGE=functional PASS`。本组会重新运行基础3项，并单独保存本次日志。

## 7 性能测试

```powershell
python tools/container.py performance
```

依次运行延迟试测、依赖链、吞吐、端到端、分段计时、加载优化及tile复用7个应用。测量窗口和计算方法见[第9章](docs/正文/09_延迟测量与软件优化分析.md)，本次周期数据查看各应用的`run.log`。

每项默认seed为1，周期上限20,000,000，运行超时上限7,200秒。全部运行成功后显示`SUITE_PASS performance 7/7`及`REPRODUCE_STAGE=performance PASS`。

## 8 查看与导出结果

```powershell
python tools/container.py collect
```

终端显示`RESULTS_ARCHIVE=...`，导出的压缩包位于宿主机`work/container-results/`。解压后主要查看：

| 材料 | 内容 |
|---|---|
| 各组的`acceptance.json` | 应用列表、逐项结果和整组是否通过 |
| 各用例的`run.log` | 应用输出、DiffTest、GOOD TRAP及性能数据 |
| 各用例的`run-result.json`、`exit-code.txt` | 运行参数、检查结果和退出状态 |
| `work/environment-checks/` | 工具版本和环境检查结果 |
| `work/build/build-logs/` | 构建命令、配置、编译输出及退出状态 |

验收以基础组3/3、功能组10/10、性能组7/7全部通过，以及对应的原始运行记录为依据。Docker退出后工作目录仍保留，后续可以继续运行或再次导出。

## 9 继续运行与常见问题

已经完成初始化的仓库，直接从尚未完成的步骤继续。构建失败后可修复问题并重新执行`build`，已有源码、编译结果和缓存会继续使用；一次只运行一个整核构建。

| 情况 | 处理方式 |
|---|---|
| 无法连接Docker | 确认引擎已启动、当前用户有访问权限；Windows使用Linux容器模式 |
| 磁盘空间不足 | 按提示补足相应磁盘空间，再重试失败步骤 |
| 下载失败 | 查看日志中的下载地址，处理网络或代理问题后重试`image`或`build` |
| 环境检查或编译失败 | 查看FAIL项及`CONTAINER_LOG`、`BUILD_LOG`指向的日志；若提示内存不足，调整Docker内存或交换空间 |
| 测试失败 | 查看该次运行的`run.log`、`run-result.json`，解决原因后重试相应测试组 |
| 初始化不完整，或源码、镜像版本与已有会话不一致 | 保留原日志；处理原因后，在新仓库副本中重新初始化 |

已完成初始化时，可用`python tools/container.py status`查看工作目录，用`python tools/container.py log`查看最近构建或测试日志。若环境镜像构建或初始化失败，直接打开终端打印的日志目录。

## 10 单用例运行与波形复查

完成构建和基础测试后，可单独运行三个基础程序：

```powershell
python tools/container.py exec python3 tools/recording_case.py hello
python tools/container.py exec python3 tools/recording_case.py vadd4
python tools/container.py exec python3 tools/recording_case.py vdot-smoke
```

每次运行创建新的结果目录。VDot-smoke结束后自动显示七例结果、DiffTest、GOOD TRAP和退出状态。需要再次查看某次结果时，将终端给出的完整`Run directory`填入：

```powershell
python tools/container.py exec python3 tools/recording_case.py vdot-smoke --result "本次Run directory的完整容器内路径"
```

报告中的波形视图和动态指令信息见[波形复查入口](recording/README.md)。仓库内的历史波形可在Windows PowerShell、仓库根目录还原，并用Windows GTKWave查看：

```powershell
python tools/prepare_recording.py
python tools/open_wave.py 1 01-fetch
```

波形输出到宿主机仓库的`work/waveforms/`。历史波形对应已保存的实验；新编译程序的地址与周期以本次运行记录为准。

## 11 已有验证记录

已在Windows Docker Desktop的独立Linux工作目录中，从提交源码完成NEMU和整核emu构建，并通过基础组3/3、功能组10/10、性能组7/7。三组共20次运行，覆盖17个不同应用，详细材料见[验证说明](VALIDATION.md)和[整核复现记录](evidence/package-checks/fullcore-local-20261103/summary.json)。

该次验证使用约9.7 GiB内存、8 GiB交换空间和2路编译。基础组约1.4分钟，功能组约18.1分钟，性能组约102.2分钟，其中性能组包含一次约16.1分钟的主机休眠。耗时供安排复现时间参考，具体取决于评审机器的配置。独立新仓库副本的初始化、环境检查、状态查询、命令执行和结果导出流程也已实际执行通过，记录链接见[验证说明](VALIDATION.md)。
