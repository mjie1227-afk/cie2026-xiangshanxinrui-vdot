# 波形、构建文件与视频

三阶段报告引用的历史波形已包含在`recording/data/`，均为原始VCD的gzip压缩数据。VADD压缩文件分为两个小于100 MiB的分卷，其余两份各为单文件。文件列表与还原信息见[波形记录](recording/waveforms.json)。

在仓库根目录执行：

```bash
python3 tools/prepare_recording.py
```

脚本自动读取分卷、解压并校验完整VCD。输出为`work/waveforms/vadd4.vcd`、`vdot-cancel.vcd`和`vdot-mixed.vcd`，合计约2.33 GB。要只解压一份，可追加`--only vadd4`、`--only vdot-cancel`或`--only vdot-mixed`；`--check-only`只核对压缩文件或已有解压文件。

GTKWave视图和打开命令在[波形复查入口](recording/README.md)。可选端口竞争小节使用仓库内保存的截图，不要求额外下载端口VCD。

`work/`、`runs/`和`recording/outputs/`为本地生成目录，不进入提交清单。emu、NEMU共享库和应用镜像通过源码构建；三份技术报告PDF、图片和压缩波形属于已准备的交付文件。3份成片分别为108.7、124.6、208.0 MiB，由Git LFS随仓库管理；入口与身份见[视频索引](videos/README.md)。`MANIFEST.sha256`覆盖源码与复现材料，视频使用 `videos/SHA256SUMS.txt` 和 `python tools/verify_videos.py` 单独校验。完整交付ZIP包含原始视频，Docker编译目录只复制源码清单中的文件，无需携带视频。
