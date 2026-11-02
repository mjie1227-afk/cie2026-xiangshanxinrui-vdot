# 第三阶段完整日志与样本归档命令

2026-10-27。用户要求先归档既有远端日志与样本，截图和录屏后续统一处理。当前状态：MIwNSR回传显示远端归档成功，10目录/264文件，包2233424字节；本地接收目录已建，等待下载与校验。具体路径、下载清单及SHA见[接收说明](server-MIwNSR/README.md)。

## 1 执行对象与产物

服务器Bash，cwd自动切换到`/root/private_data/mj/xiangshan`；复制[server-paste-command.txt](server-paste-command.txt)全文执行。仅使用已有Python3标准库读取文件、计算哈希和生成tar.gz；不启动make/Mill/emu/NEMU，不执行或导入旧运行目录中的脚本。

创建全新的`evidence/stage3-log-archive-XXXXXX/`，不覆盖旧目录。成功后有：

- `stage3-logs.tar.gz`：完整选中日志/样本/元数据，保持`evidence/<原run>/...`路径；另含manifest、SHA256SUMS、preflight和本次collect.py。
- `manifest.json`、`SHA256SUMS`：每个来源文件相对路径、字节数、SHA256；`preflight.json`保存必需目录与排除项。
- `stage3-logs.tar.gz.sha256`：压缩包本身的SHA256。
- `collect.py`、`collect.log`、`collection-result.json`、`exit-status.txt`：本次归档脚本、日志、结果和真实collector/tee退出码。

不截断原日志，也不重新生成samples或统计。只复制已保存的运行身份记录，不重新哈希当前emu/NEMU/应用二进制。各文件在读取/打包前后核对大小、时间及文件身份，压缩后逐成员重算SHA256并比较；归档通过只证明这些文件收集一致，不代表又执行了一次硬件验收。

## 2 收集范围

以下路径相对服务器`evidence/`，共10个固定目录，不扫描整个服务器。

| 目录 | 用途 |
|---|---|
| `vdot-rvv-equiv-8nvimb` | 两种RVV等价，144例/432调用完整运行日志 |
| `vdot-timing-retry-5vHUp8` | 计时预检成功，42次调用的样本/统计；使用独立重试布局 |
| `vdot-chain-KiI3xX` | 依赖链，40次调用及30个正式样本 |
| `vdot-tput-uLgHm6` | 八路批处理，40次调用及30个正式样本 |
| `vdot-e2e-bijzGZ` | 小数组，40次调用及30个正式样本 |
| `vdot-timing-pilot-IgNim5` | 原应用构建、矩阵、镜像身份和900秒超时原日志 |
| `vdot-build-80mKCD` | 首版源码NEMU/emu构建与smoke，支撑C3.1.1 |
| `vdot-matrix-OMcrpf` | 原mtval失败与重叠成功，支撑定位案例 |
| `vdot-mtval-build-xYGYlZ` | mtval修复构建、异常/重叠/smoke/Hello/VADD回归 |
| `vdot-pipeline-JuGUz6` | 120例依赖/混发/分支异常CSR架构套件 |

递归保存这些目录内的`.log/.txt/.json/.csv/.tsv/.sha256/.argv/.env/.exit/.nm/.disasm/.patch/.diff/.config/.md/.yaml/.yml/.py/.sh`及轮转/压缩`.log`文件、stdout/stderr。涵盖运行日志、构建日志、完整逐轮样本、原统计、结果、参数、环境、身份、符号和反汇编等已有材料。

波形、emu、参考库、镜像及其他不在上述范围的文件不入包，逐项列在excluded中，不静默丢弃。等价批次本身没有独立计时samples.json，不将其列为必需；其432调用结果留在完整日志。预检重试不要求不存在的console.log/exit-status.txt，而收集run-result.txt/script-result.txt、expected.sha256及start/end；原构建信息由IgNim5补充。

## 3 成功信号与停止条件

必须同时看到`STAGE3_ARCHIVE_READY`、`COLLECTOR_EXIT=0`、`TEE_EXIT=0`和`STAGE3_ARCHIVE_SCRIPT_EXIT=0`，并保存最后打印的ARCHIVE、ARCHIVE_BYTES、ARCHIVE_SHA256。完成后下载tar.gz、其.sha256及collection-result.json；在本地校验压缩包后再更新“完整日志已归档”。

必需目录/日志/样本缺失、路径为符号链接、空间不足、源文件在收集中变化或包内哈希不一致，均停止。保留新目录和collect.log/preflight.json用于定位，不删旧证据、不重跑仿真。旧OMcrpf的退出1和IgNim5超时属于应保留的历史证据，不是本次归档失败。

## 4 本地检查

[local-check.json](local-check.json)记录小型合成夹具：源文件不变、嵌套原日志逐字保留、历史退出1保留、VCD排除清单、缺样本提前停止及tar成员哈希检查均通过。原始工具输出见[fixture-success.log](fixture-success.log)。

WSL/Bash语法检查及整段wrapper执行退出0，日志见[wrapper-fixture.log](wrapper-fixture.log)。该执行仅把work替换为本地夹具目录，不连接服务器；产生的小测试包不是项目实测证据。实际服务器是否存在全部必需文件，以用户随后执行结果为准。
