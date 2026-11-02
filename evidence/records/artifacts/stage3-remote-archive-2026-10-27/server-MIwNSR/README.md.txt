# MIwNSR完整日志与样本：本地核验通过

2026-10-27。5个下载文件已接收，压缩包2233424字节，SHA256=48882ae468149dadc6aadb2303cb9d25f035f5feea49e13cd945c8e3baf54cc8，与远端回传、.sha256及collection-result一致。

[核验结果](local-verification.json)退出0：264来源文件/55489484字节、10运行目录，加4项清单/脚本共268成员，全部成员与manifest/SHA256SUMS匹配。原包保留，[unpacked](unpacked/)保存逐成员验证后的副本，路径仍为evidence/原run/文件。唯一排除项为16字节boot-flash.bin，不是缺失日志。

四组完整计时样本共162调用（36预热/126正式），原日志、JSON和CSV逐条一致；顺序/instret/consumer正确，36组统计重算一致。[逐轮复算表](complete-samples.md)。8nvimb完整日志含144例/432调用/两基线通过标记，不当作逐调用计时样本。

[最终检查日志](local-verification.log)与[首次停止日志](local-verification-first.log)保留。首次比较开发文件而非实际heredoc，因多一个末尾换行停止；更正为比对当时交付命令后逐字一致，未修改压缩包。归档工具本身的耗时为13.921秒，不是硬件仿真耗时。

本包无需再次下载、生成或仿真。第一、二阶段的后续缺口及仅补缺失项命令见[归档状态](../../../reports/archive-status.md)。截图、录屏继续后置。
