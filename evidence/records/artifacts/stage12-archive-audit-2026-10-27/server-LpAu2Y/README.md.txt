# LpAu2Y第二阶段补包：本地核验通过

2026-10-27。5个下载文件保留原名；包90483004字节，SHA256 `0a834faa0e83f1c27dbfa7f836f5e62bca0342332d5a0b375a3dcbb56ab2e07b`。132成员/128来源文件/1050781192字节均与manifest/SHA256SUMS一致，已解包到[unpacked](unpacked/)，不重复下载或执行远端采集。

[本地核验结果](local-verification.json)和[日志](local-verification.log)保存具体检查。7项排除为3个pycache、3个已在本地且内容一致的JSON、已有EfQru1 VCD。3个JSON的实际本地位置在验证结果的verified_local字段；不强行在新目录重复复制。

原退出文件保存collector/tee均0，外层SCRIPT_EXIT=0来自用户回传，不在该文件。首次核验误读这个文件约定而停止，修正后通过；[首轮日志](local-verification-first.log)保留。没有运行归档内代码、构建或仿真。

两份VCD声明区及代表性保存事件也已核对，用于准备[波形截图操作卡](../../../recording/stage2/wave-cards.md)；未重新扫描VCD事件正文。[归档状态](../../../reports/archive-status.md)。
