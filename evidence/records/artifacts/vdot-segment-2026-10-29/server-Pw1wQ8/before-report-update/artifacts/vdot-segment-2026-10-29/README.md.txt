# 分段长点积补测：操作与回传

2026-10-29。全局位置：第三阶段 C3.3 的扩展实验。既有延迟/批处理/小数组结果保留；本次新增应用 `vdot-segment-v1`，验证较少中间存储的分段归约。原理与语义见[应用说明](../../benchmarks/rvv-baseline/vdot-segment-v1/README.md)。

当前状态：本机编译、26 个函数输入检查、完整 main 与错误期望负向检查通过；服务器测量未执行，硬件收益未确定。

## 1 新增什么、编译谁、运行谁

`main.c` 负责数据与检查，`cases.S` 负责三条点积路径及两种结果组织，`Makefile` 只构建新应用。服务器 runner 先核对已有成功 E2E 记录、源码计时依据、emu/NEMU/Flash 哈希及进程，再将新源码复制到 `vdot-dev-20261024/nexus-am/apps/vdot-segment-v1`，使用 GCC 12 生成新 ELF/BIN，最后由原 `emu` 加载新镜像、原 NEMU 和 Flash。

不会运行 `make emu`、NEMU 构建或旧测试；已有同名新应用、身份不匹配、已有重型构建/仿真时停止。没有删除/覆盖成功产物的命令。

## 2 执行

### 第一步：Windows PowerShell 复制完整命令

在本机 PowerShell 执行；路径可直接使用：

```powershell
Get-Content -LiteralPath 'D:\Mayyyyyy\WorkSpaces\日常工作区1\2026比赛规划\RISCV_vdot\artifacts\vdot-segment-2026-10-29\server-paste-command.txt' -Raw | Set-Clipboard
```

也可打开[完整服务器命令](server-paste-command.txt)，全选复制。文件包含完整源码压缩包的 base64，因此终端输入较长；它负责传递文件，实际开发内容仍是上面的 C/汇编和运行脚本。

### 第二步：服务器 SSH / Bash 粘贴执行

在服务器 Bash 终端确认位置，然后粘贴第一步复制的完整内容：

```bash
cd /root/private_data/mj/xiangshan
pwd
```

命令以 `bash <<'VDOT_SEGMENT_COMMAND'` 开始，以独立一行 `VDOT_SEGMENT_COMMAND` 结束；不要加反斜杠或自行删换行。若已经使用 tmux，建议在其会话中运行；普通 SSH 终端请保持连接。

成功启动后先打印 `PACKAGE_DIR=...` 和 `LOG_DIR=...`，随后 `RUNNING=build`、`BUILD_EXIT=0`、`RUNNING=architecture`。构建上限 300 秒，整核运行上限 7200 秒及 2,500,000 模拟周期；每 60 秒输出进度。7200 秒是保护上限，不是完成时间预测。

### 第三步：确认完成标志

应同时出现：

```text
BUILD_EXIT=0
ARCHITECTURE_EXIT=0
PASS VDOT_SEG calls=52 samples=39 warmups=13 variants=13 outputs128=1 scratch=1 guards=1 inputs=1 state=1
HIT GOOD TRAP
VDOT_SEG_READY samples=39 warmups=13
SEG_SCRIPT_EXIT=0
TEE_EXIT=0
```

参考库行与 `Difftest enabled.` 也由脚本核验。若出现 `SEG_ERROR`、非零退出、超时或周期上限，保留 `LOG_DIR`，回传错误及目录即可；不要重新粘贴整个命令、删除应用或重建 emu。

## 3 保存在哪里

| 文件位置（相对服务器项目根） | 内容 |
|---|---|
| `evidence/vdot-segment-package-XXXXXX/` | 传输包、校验文件、运行脚本 |
| `vdot-dev-20261024/nexus-am/apps/vdot-segment-v1/` | 新应用源码和 ELF/BIN |
| `evidence/vdot-segment-XXXXXX/`（LOG_DIR） | 本次构建、运行、原始样本和统计，失败时也保留 |

LOG_DIR 中重点文件：`console.log`、`exit-status.txt`、`result.json`、`architecture.log`、`architecture-check.json`、`samples.json`、`samples.csv`、`raw-statistics.json`、`comparisons.json`、`perf-context.json`、`runtime-identities.json`、`kernel-identities.json`、`matrix.json`、构建/运行 argv 与耗时。

`comparisons.json` 分开给出：相同 G 的 RVV/VDot 比值，以及相同路径相同 G 的物化/寄存器组织比值。`perf-context.json` 是全应用计数线索，不作单个内核的 Sbuffer 等待占比。

## 4 回传

先回传终端最后的完成/失败输出和 `LOG_DIR`。随后从 VS Code 远程文件浏览器下载整个 LOG_DIR（不下载 emu/NEMU），保存到本机：

```text
D:\Mayyyyyy\WorkSpaces\日常工作区1\2026比赛规划\RISCV_vdot\artifacts\vdot-segment-2026-10-29\server-实际六位后缀\
```

其中 `server-实际六位后缀` 替换成日志目录实际后缀，例如 `vdot-segment-Ab12Cd` 对应 `server-Ab12Cd`。不要覆盖其他 server 目录。

## 5 已执行的本机检查

- [本地结果](local-180217/result.json)与[完整 main 输出](local-180217/main.txt)：构建退出 0，26 个函数检查，52 调用通过，错误期望返回 1。
- [内核指纹](kernel-identities-local.json)：13 个函数的机器码、静态范围及动态退休数。
- [交付检查](delivery-check.json)：6 项综合检查通过；[构建检查日志](package-check.log)。初次打包脚本的 Path 拼接错误已修正，错误日志单独保留，应用检查无需重跑。
- [包校验](package.tar.gz.sha256)、[包](package.tar.gz)与[完整命令](server-paste-command.txt)。

服务器返回后再更新正式性能表、图像与演示稿。物化对照多出明确的中间存储和重读，可观察消去该步骤的收益；是否由某个硬件资源主导，需要匹配窗口的进一步证据。
