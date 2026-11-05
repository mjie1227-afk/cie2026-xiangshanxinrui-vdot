# 三阶段演示视频

三阶段录屏已完成，对应[技术报告](../docs/README.md)的环境与执行过程、指令设计与功能验证、协同验证与性能分析。

3份MP4使用Git LFS随仓库管理，文件名与对应阶段如下。克隆后先下载LFS文件，再校验视频；编译和运行测试不依赖视频下载。

| 阶段 | 内容 | 附件文件名 | 时长 | 大小 |
| --- | --- | --- | --- | --- |
| 阶段1 | 环境、Hello/VADD 与向量指令执行过程 | `第一阶段的操作过程录屏.mp4` | 09:35 | 108.7 MiB |
| 阶段2 | 指令设计、RTL 接入与基础功能测试 | `第二阶段的设计文档和基础测试文档.mp4` | 10:22 | 124.6 MiB |
| 阶段3 | 协同验证、波形分析与性能总结 | `第三阶段的基于波形仿真和性能分析录屏.mp4` | 15:22 | 208.0 MiB |

3份视频均为1920×1080、30帧/秒，H.264画面与AAC立体声音轨。2026-11-05完成全长音视频解码检查，退出码均为0，并抽查每份视频的6处画面。文件信息与SHA256见[视频清单](manifest.json)和[校验值](SHA256SUMS.txt)。

在已安装Git LFS的机器上，进入仓库根目录执行：

```powershell
git lfs install --local
git lfs pull
python tools/verify_videos.py
```

成功应显示3份视频均为 `OK` 和 `VIDEOS_CHECK=PASS`。若文件仍是LFS指针，检查器会提示先运行 `git lfs pull`。安装Git LFS的方法见[GitHub文档](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage)。Linux将 `python` 替换为 `python3`。

`MANIFEST.sha256`覆盖源码、报告与复现工具，视频使用[独立校验值](SHA256SUMS.txt)。这样只下载源码时仍可编译，下载视频后可单独核对文件完整性。项目提供的完整交付ZIP包含3份原始MP4；GitHub网页自动生成的源码ZIP是否含视频取决于其LFS归档设置，推荐通过Git与Git LFS克隆。
