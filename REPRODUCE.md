# 源码恢复、编译与运行

上游版本、补丁和依赖由 [upstream-lock.json](configs/upstream-lock.json)固定。XiangShan 为 `16ae9ddcda54fc9a2fddffad73174cf793ac7814`，NEMU 为 `a48a11f208ff81ad765591d83271d1b339fb3861`，nexus-am 为 `086a238062fdfb3281b745a537b361983d0154b5`。

## 1 环境

使用 Linux 或 Ubuntu WSL，将源码和构建目录放在 Linux 文件系统，例如 `~/cie-vdot-work`。保存的服务器构建采用 JDK 21、Mill 0.12.3、Verilator 5.052、Clang 19、RISC-V Linux GNU GCC 12；阶段一使用的 GCC 13.3.0 另见报告。还需要 Git、GNU Make、Python 3.9 或更新版本、NEMU 构建所需的基础开发库。完整历史环境在第一阶段报告及 NEMU/emu 构建记录中。

准备新目录时不要求复用历史二进制的 SHA256；新的编译结果应记录自己的身份。既有成功运行使用的身份已保留在 evidence 中。

## 2 恢复源码

以下在 **Linux / WSL Bash**、本作品仓库根目录执行。先查看计划，再恢复到尚不存在的目录：

```bash
python3 tools/restore_sources.py "$HOME/cie-vdot-work" --plan
python3 tools/restore_sources.py "$HOME/cie-vdot-work"
```

工具克隆锁定上游及依赖，分别应用 `XiangShan-full.patch` 和 `NEMU.patch`，核对 19 个修改文件，再复制 NEMU 配置、17 个应用和 Flash。成功打印 `SOURCE_RESTORE_OK`，过程写入新目录的 `restore.log`。目标存在、下载失败或补丁不匹配时停止并保留日志。

`XiangShan-full.patch` 已包含正式 VDot 与 mtval 修复，只应用一次。`src/` 内的文件是相同修改的阅读快照。

## 3 分别编译

仍在本作品仓库根目录执行。先编 NEMU，再编 emu；同时只运行一个整核构建。

```bash
bash tools/build.sh "$HOME/cie-vdot-work" nemu
bash tools/build.sh "$HOME/cie-vdot-work" emu
bash tools/build.sh "$HOME/cie-vdot-work" app vdot-smoke
```

NEMU 使用保存的 `.config`；emu 使用 `MinimalConfig / NUM_CORES=1 / EMU_TRACE=1 / JVM_XMX=6G`。应用使用 `ARCH=riscv64-xs / MARCH=rv64gcv`。需要指定工具位置时设置 `VDOT_CC`、`VDOT_CXX`、`VDOT_RISCV_CC`；`VDOT_JOBS` 默认 4，应用默认 2。

每步打印 `BUILD_LOG` 和真实 `BUILD_EXIT_CODE`。退出码为 0 后再进入下一步，错误详情见对应 `build.log`；脚本不会清理旧目录，也不会将编译失败忽略为成功。

预期文件为：

```text
~/cie-vdot-work/NEMU/build/riscv64-nemu-interpreter-so
~/cie-vdot-work/XiangShan/build/emu
~/cie-vdot-work/nexus-am/apps/vdot-smoke/build/vdot-smoke-riscv64-xs.bin
```

## 4 运行一个整核用例

下列命令仅运行已编译的 smoke 镜像，在新的运行目录保存日志。`--reference` 显式指定支持 VDot 的 NEMU 库，Flash 默认为仓库中的 16 字节启动镜像。

```bash
python3 tools/run_case.py vdot-smoke \
  --emu "$HOME/cie-vdot-work/XiangShan/build/emu" \
  --reference "$HOME/cie-vdot-work/NEMU/build/riscv64-nemu-interpreter-so" \
  --image "$HOME/cie-vdot-work/nexus-am/apps/vdot-smoke/build/vdot-smoke-riscv64-xs.bin" \
  --output "$HOME/cie-vdot-runs/smoke-01" \
  --max-cycles 3000000 --timeout 1800
```

先检查输入时可追加 `--dry-run`，此时只打印参数与身份、不运行 emu。真实执行只有同时满足进程退出 0、应用 PASS、DiffTest 已启用、正确参考库路径及 GOOD TRAP 时才返回通过。

`run-result.json` 保存 cwd、argv、相关环境、种子、周期上限、主机超时、文件 SHA256 和检查结果；原始输出位于 `run.log`，被测进程退出码位于 `exit-code.txt`。再次运行时使用新的 `--output` 目录。

## 5 其他应用与性能

按 [apps 列表](apps/README.md)替换构建命令的应用名，再给运行工具传入对应镜像。推荐先完成 `vdot-exceptions`、`vdot-overlap`，再做三项流水套件和 RVV 等价。

性能应用仍使用 seed=1。可为性能运行使用 `--max-cycles 20000000 --timeout 7200`，这两个参数是运行上限，窗口周期来自应用的 mcycle 读数。运行后保留所有预热与正式输出，按报告方法统计；具体历史样本见 evidence。

## 6 波形

录波需使用带 `EMU_TRACE=1` 的 emu，另加 `--dump-wave-full --wave-path=<新VCD路径> -b <起点> -e <终点>` 等导出参数。按程序实际执行时间选择窗口；保存的正常、取消和竞争事件位置来自各自历史运行。原波形的来源、大小与窗口见 [LARGE_FILES.md](LARGE_FILES.md)。

本仓库准备阶段只做源码恢复与脚本检查，未重新构建处理器或重跑这些硬件实验。
