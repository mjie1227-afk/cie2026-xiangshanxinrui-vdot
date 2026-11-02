# 大型波形与生成文件

作品 Git 仓库包含完整指令改动、测试源代码、报告图片、原始日志与样本。以下大型波形保留在原工程中，未放入 Git；GitHub 普通 Git 单文件上限为 100 MiB，分发这些文件可另用 Release 或按复现步骤重新导出。[GitHub 官方说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

| 波形 | 原文件大小 | 原始来源 |
| --- | --- | --- |
| VADD 生命周期 | 1395708089 字节 | 第一阶段 `vadd4.vcd`，2026-10-17 运行 |
| 正常执行/分支取消/CSR | 457224402 字节 | `vdot-wave-window-Cpa0HX/cancel-window.vcd` |
| VADD/VMUL/VDot 混发 | 477548918 字节 | `vdot-mixed-wave-FNmKGI/mixed-window.vcd` |
| VDot/VIOTA 发射前竞争 | 481830060 字节 | `vdot-port-EfQru1/port-window.vcd` |

对应截图、事件记录与实际应用源代码已随仓库提供。报告第 3、6 章解释所选实例的身份、信号、窗口与读数；原始来源和本地证据的对应关系见[证据索引](evidence/index.md)。

编译生成的 emu、NEMU 共享库、ELF/BIN、构建缓存和中间压缩包同样不进入 Git。`configs/boot-flash.bin` 为 16 字节启动代码，与保存的实验 Flash 哈希一致，单独随仓库提供。

如另外上传波形或视频到 Release，请在本页补充实际下载链接、文件大小及 SHA256。当前没有发布大文件下载链接。
