# 验证记录与版本对应

本页记录 2026-11-02 整理作品仓库时的检查。硬件结论来自仓库保留的成功运行记录，本次未重新编译处理器或运行整核仿真。

## 源码与补丁

从实际 Git 对象导出锁定版本的干净源码到新的 Linux 临时目录，分别执行 `git apply --check` 和 `git apply`。XiangShan 的 15 个文件、NEMU 的 4 个文件与正式修复后的快照 SHA256 全部一致。原开发目录及其未提交修改保持原样。

- [补丁检查原始记录](evidence/package-checks/patch-validation.json)：命令、退出码、上游版本和临时目录。
- [源文件哈希](configs/source-snapshots.json)：19 个修改/新增文件。
- [上游与依赖版本](configs/upstream-lock.json)：XiangShan、NEMU、nexus-am 及实际使用的依赖。

15 个阶段二/三应用的 45 个构建输入已与保存的服务器交付包或交付目录逐文件比较，交付版本字节一致。Windows 副本中有 24 个文件仅换行格式不同，本仓库采用当时交付包内的 LF 原件。Hello、VADD 来自既有阶段一源码，其复制来源和哈希另列在来源清单中。

- [应用源码核对](evidence/package-checks/app-source-check.json)
- [复制来源清单](evidence/source-manifest.json)：记录输入文件来源；报告 Markdown 的链接在复制后按本仓库目录调整，交付文件最终哈希以根目录清单为准。

NEMU 配置与既有服务器配置一致；16 字节 Flash 按锁定 DiffTest 源码中的启动内容生成，并与成功实验 Flash 的 SHA256 一致：`fea548655a8b6eecacace83e2f4380a18b8aa83bce964c8aae4cffbe2f5a9724`。

## 新增复现工具

新增工具用于在新目录恢复源码、分步编译及保存单次运行记录。15 项辅助检查通过，包含日志判定、缺失输入、已有目录保护、Bash 语法，以及模拟进程的正常退出、失败、超时和 Ctrl+C 清理。检查使用人工构造的日志和小型模拟进程，原始结果见 [helper-check.json](evidence/package-checks/helper-check.json)。

在 **Linux / WSL Bash**、本仓库根目录可以重复这些轻量检查：

```bash
python3 tools/check_helpers.py
```

成功结果为 `failed: 0`，退出码 0。源码恢复工具的完整网络下载流程与后续重型构建未在本次打包中重跑；补丁的实际应用已经按上节完成。

## 交付文件

在 **PowerShell 或 Linux**、本仓库根目录执行：

```text
python tools/verify_bundle.py
```

成功结果为 `bundle-check-passed`，`errors` 为空，退出码 0。检查包括最终文件清单、19 个源文件哈希、本地 Markdown 链接、17 个应用的 Makefile 源文件引用和普通 Git 单文件大小限制。

更新视频链接或其他文件后，先审阅改动，再重建清单并检查：

```text
python tools/make_manifest.py
python tools/verify_bundle.py
```

## 实验结果入口

原始运行、统计和图表沿用三阶段报告中的编号。完整入口见 [evidence/index.md](evidence/index.md)；阶段二包括 mtval 修复回归、异常、重叠、流水及代表性波形事件；阶段三包括 RVV 等价、依赖链、批处理、小数组、分段归约、加载优化和 2×2 输入复用。

三段录屏当前仍为 0/3 已验收成片；视频链接和在线提交状态见 [videos/README.md](videos/README.md)及根目录说明。
