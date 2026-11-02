# VDot 执行期非法指令的 mtval 修复

状态：**服务器新emu构建及全部五项应用验收已通过**，VDOT_MTVAL_ACCEPTANCE_PASS/退出0；原mtval差异在本批范围关闭。[回传核验](server-xYGYlZ/review.json)、[新身份](server-xYGYlZ/accepted-identities.sha256)。异常64例、重叠60例、smoke7例、hello-meijie/VADD全部DiffTest/GOOD TRAP。以下命令与本地记录保留供追溯，不重放成功构建。

## 修复内容

旧失败见[诊断](../vdot-matrix-2026-10-24/server-OMcrpf/diagnosis.md)：case1 short-1-vm0在PC0x8000021c触发EX_II，NEMU mtval=0x0020818b、DUT=0。已有TrapInstMod只跟踪译码/CSR异常，执行期才发现的短VL异常没有携带机器码。

本次[窄修复补丁](repair-only.patch)修改三个已有文件，新增一个功能模块：

- `backend/rob/VdotTrapInst.scala`：按ROB槽位保存16个可变编码位、generation flag和VDot分类，共每槽18位；每次分配（含普通指令）更新分类，查询时匹配完整ROB指针。不使用DebugMem。
- `backend/rob/Rob.scala`：分配时保存字段；仅在真实ROB异常选择时生成结果，排除中断，下一拍与`io.exception`对齐。取消后没有真实trap便不输出；新分配覆盖旧槽位。
- `backend/Bundles.scala`：ExceptionInfo新增`vdotTrapInst`，随已有异常包传输。
- `backend/fu/wrapper/CSR.scala`：只有当前VDot的EX_II使用ROB提供的指令；其他事件沿用原TrapInstMod。原CSR/译码异常仲裁、NEMU配置和DiffTest比较均未修改。

保留原始指令身份直到ROB精确异常选择，避免把所有合法VDot提前塞进单槽异常记录器，也避免按FU完成先后覆盖较老异常。18位/槽是RTL存储字段计数，不是面积或时序测量。

## 本地验证

真实源码：`/home/lenovo1227/xs-vdot-dev/XiangShan`，HEAD=16ae9ddcda54fc9a2fddffad73174cf793ac7814，保留此前未提交VDot修改。本轮未commit/add/push，未修改NEMU或旧emu。只对本次源码及相关工程状态检查。

1. [局部RTL结果](mill-172742/result.json)，[日志](mill-172742/run.log)：`mill -i -j 2 -Djvm-xmx=6G xiangshan.test.testOnly xiangshan.backend.rob.VdotTrapInstTest`，退出0。实际Verilator执行65536种可变字段编码及13项条件检查，经过生产`VdotTrapInstTable`、生产选择函数和真实`TrapEntryMEventModule`，核对mtval。覆盖故障机器码、年轻条目干扰、generation不匹配、同/不同generation槽位复用、中断/非非法排除、CSR/压缩指令legacy选择和reset失效。
2. [整核展开](mill-172910/result.json)，[日志](mill-172910/run.log)：MinimalConfig、单核、DiffTest、CHIRRTL，退出0，135条elaboration警告保留。产物在`/home/lenovo1227/xs-vdot-dev/elaborate-vdot-mtval-20261024`，未扫描大FIRRTL。后端对新增ExceptionInfo字段按整包传输；NewCSR同拍hasTrap驱动事件，和选择器有效期一致。
3. [交付验证](validation.json)：完整补丁从固定HEAD文件夹具应用成功，15份修复后源码哈希匹配，且被测源码未改变；Bash语法、Python编译、压缩包与内嵌base64一致性通过。夹具位于/mnt/d，Git报告文件执行位100755/100644警告，但应用退出0、内容哈希一致；实际构建目标为Linux原生文件系统。

首个局测[mill-172650](mill-172650/run.log)因测试夹具把没有零编码的CSR枚举整体初始化为0而失败；改为只约束mtval通路输入后通过，生产修复代码未因此改变。局测模拟ROB的真实trap条件，未运行完整ROB乱序调度/取消竞争；这部分不能由上述条件检查宣称覆盖。CHIRRTL成功也不等于服务器DiffTest成功。

## 服务器执行（已完成，命令仅供追溯）

将[server-paste-command.txt](delivery-v2/server-paste-command.txt)全文粘贴到服务器Bash。cwd=/root/private_data/mj/xiangshan；无需上传文件。命令自带校验包，先检查旧源码状态/哈希和固定产物，再克隆新XiangShan及实际存在且HEAD匹配的依赖仓库，应用完整源码补丁。

- 新副本：`/root/private_data/mj/xiangshan/vdot-mtval-fix-20261024/XiangShan`；已有该目录即停止，不覆盖、不删除。
- 新emu：该目录下`build/emu`，MinimalConfig、单核、EMU_TRACE=1、JVM_XMX=6G、make -j4，构建墙钟上限4小时。
- NEMU：继续使用`vdot-dev-20261024/NEMU/build/riscv64-nemu-interpreter-so`，SHA256=11b9f6807c36ed860e0c64cc4e58d27216b19335ecde1ce5797ba2d1cd057b74；不配置、不编译。
- Flash：继续使用`evidence/vdot-build-80mKCD/boot-flash.bin`，SHA256=fea548655a8b6eecacace83e2f4380a18b8aa83bce964c8aae4cffbe2f5a9724。
- 原异常镜像SHA256=e52ef47823bee34fded28c9d0aa96b924a17fff6fda52ca36aa7ccf4f2f19302；不重编或跳过用例，先跑这份64例矩阵，case1即原失败点。
- 随后在**新emu**回归重叠60例、VDot smoke7例、hello-meijie、VADD。旧emu不再运行。
- 每个应用显式`--diff`、`-F`、seed1、no-snapshot，300万周期/1800秒上限。遇失败立刻停止，保留所有日志；不能关闭比较继续。

完整构建/运行日志、argv、镜像身份和退出码存入新`evidence/vdot-mtval-build-*`。所有阶段通过且固定产物前后身份不变，才输出`VDOT_MTVAL_ACCEPTANCE_PASS`和`VDOT_MTVAL_EXIT=0`。请回传终端摘要、LOG_DIR以及打印的新emu/参考库SHA256。若停在某阶段，回传该阶段末段与退出码，勿重放整个包或删目录绕过检查。

交付包最终使用delivery-v2：预交付检查发现手工独立克隆的嵌套仓库在git submodule status中显示未初始化，已改为按gitlink递归检查真实.git/HEAD，并固定13个已用于本地展开的依赖仓库。旧delivery仅保留追溯，不能使用；该修正后的delivery-v2随后已在服务器成功执行，见本页顶部验收记录。
