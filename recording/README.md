# 波形复查

本目录保存报告对应的历史波形压缩数据、身份清单和 GTKWave 视图。环境准备、编译与程序运行见[复现指南](../REPRODUCE.md)，波形分析见[技术报告](../docs/README.md)。

在仓库根目录的 Windows PowerShell 中还原三份波形，再打开 VADD 取指视图：

```powershell
python tools/prepare_recording.py
python tools/open_wave.py 1 01-fetch
```

还原文件位于宿主机仓库的 `work/waveforms/`。GTKWave 需在本机可用；工具会解析保存视图中的波形路径。若只复查 VADD，可用 `python tools/prepare_recording.py --only vadd4`。

| 材料 | 位置 |
| --- | --- |
| 原始波形身份、压缩文件与还原信息 | [waveforms.json](waveforms.json) |
| VADD 视图 | [stage1/views](stage1/views) |
| VDot 执行、取消和退休状态请求视图 | [stage3/views](stage3/views) |
| 压缩数据与分卷说明 | [大文件说明](../LARGE_FILES.md) |

这些视图对应已保存的实验。用 PC、机器码、完整 ROB 和物理目的寄存器追踪同一动态指令；新构建程序的地址及周期以本次运行记录为准。
