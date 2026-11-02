# MIwNSR归档包接收目录

2026-10-27。服务器回传显示归档成功，10个运行目录、264个文件、原始55489484字节；压缩包2233424字节。collector/tee/script均0。完整输出选段见[user-returned-summary.txt](user-returned-summary.txt)，[核验状态](review.json)仅接受远端回传，本地包尚未收到或校验。

从服务器`/root/private_data/mj/xiangshan/evidence/stage3-log-archive-MIwNSR/`下载以下5个文件到本目录，保留文件名：

| 文件 | 作用 |
|---|---|
| stage3-logs.tar.gz | 实际日志与样本压缩包 |
| stage3-logs.tar.gz.sha256 | 压缩包的SHA256校验值，用于检查下载字节是否一致；不是压缩包，也不是密码 |
| collection-result.json | 本次归档结果，含来源文件数、大小、包路径、哈希、耗时和退出码 |
| collect.log | 归档工具原始输出，保留执行过程 |
| exit-status.txt | collector与tee的退出码及输出目录 |

manifest.json、SHA256SUMS、preflight.json和collect.py已经包含在包内，无需单独下载。包内排除1项，具体名称待读取preflight确认，不补猜。

收到后应核对包大小为2233424字节、SHA256为`48882ae468149dadc6aadb2303cb9d25f035f5feea49e13cd945c8e3baf54cc8`；再检查包内成员与manifest/SHA256SUMS一致，并对照完整samples、统计和result。全部通过后才记“本地原始日志已归档”。此时无需重新运行服务器归档、仿真或构建。

第一、二阶段也要保留本地原始证据。现有材料先复用，本包已含首版构建、mtval失败/修复和120例等第二阶段证据；后续按阶段索引补缺失项，大型VCD单独保留。轻量分享包与自己保存的完整证据档案目的不同，不因分享包可省略波形而删除原波形。
