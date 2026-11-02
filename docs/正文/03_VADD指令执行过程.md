# 3 VADD 指令执行过程

程序算出正确结果后，还需要解释这条指令如何经过香山前端、乱序后端和提交路径。本章选择一次 `vadd.vv v3,v1,v2` 执行，先确认输入输出，再从取指块追踪到译码、重命名、发射、计算、物理寄存器写入和已提交映射更新。整个分析始终跟踪同一次动态执行，避免把相同 PC 在不同时刻的活动混在一起。

## 3.1 测试程序和波形来源

测试配置为 VLEN=128、SEW=32、LMUL=1、VL=4，无掩码执行。数组 A=`[1,2,3,4]`、B=`[10,20,30,40]` 分别进入 v1、v2，结果存回 C。核心汇编如下：

```asm
li t0, 0x200
csrs mstatus, t0
csrwi vstart, 0
vsetvli t1, a3, e32, m1, ta, ma   # a3=4，检查实际VL
bne t1, a3, .Ldone
vle32.v v1, (a0)
vle32.v v2, (a1)
vadd4_target:
vadd.vv v3, v1, v2
vse32.v v3, (a2)
.Ldone:
mv a0, t1
ret
```

C 程序将输出预填为 −1，并逐项比较独立期望。运行读回 `vlenb=16`，确认 128 位向量宽度，随后给出四项结果和正常结束标志：

```text
vadd4: VL=4 SEW=32 LMUL=1 VLEN=128 bits
C[0] = 11 (expected 11)
C[1] = 22 (expected 22)
C[2] = 33 (expected 33)
C[3] = 44 (expected 44)
PASS: vadd.vv produced [11, 22, 33, 44]
Core 0: HIT GOOD TRAP at pc = 0x8000023c
```

![VADD程序逐项检查与正常结束记录](../assets/stage1/01-program-pass.png)

图 3-1　VADD 应用结果。结束陷阱位于 `0x8000023c`，本章追踪的加法指令位于 `0x80000148`。

应用和仿真器分别构建。以下命令在第一阶段的 WSL/Bash 环境中编译应用，然后创建新的波形目录运行同一镜像：

```bash
export AM_HOME=/home/lenovo1227/xiangshan-learning/nexus-am
XS_ENV=/mnt/d/Mayyyyyy/WorkSpaces/VScode/xs-env
cd "$AM_HOME/apps/vadd4"
make ARCH=riscv64-xs LINUX_GNU_TOOLCHAIN=1 MARCH=rv64gcv -j2

mkdir -p "$HOME/xiangshan-learning/waves"
wave_dir=$(mktemp -d "$HOME/xiangshan-learning/waves/vadd4-XXXXXX")
cd "$XS_ENV/XiangShan"
./build/emu \
  -i "$AM_HOME/apps/vadd4/build/vadd4-riscv64-xs.bin" \
  --diff "$XS_ENV/XiangShan/ready-to-run/riscv64-nemu-interpreter-so" \
  --no-snapshot --dump-wave-full \
  --wave-path="$wave_dir/vadd4.vcd" \
  -b 0 -e 8000 -C 200000 -s 0 \
  > "$wave_dir/run.log" 2>&1
wave_rc=$?
printf 'EMU_EXIT_CODE=%s\n' "$wave_rc" | tee "$wave_dir/result.txt"
```

`--dump-wave-full` 导出完整层级，`-b/-e` 选择仿真 cycle 窗口，`-C` 限制总周期，`-s 0` 与归档运行的种子一致。首次运行和导波形运行均通过 DiffTest，退出码为 0。复现时可利用生成的 ELF/反汇编定位符号，再在 GTKWave 中载入 VCD；操作入口见原波形指南[〔6〕](../../evidence/records/exercises/vadd4/WAVE.md.txt)。

## 3.2 如何确认追踪的是同一次执行

反汇编中的 PC=`0x80000148`、机器码=`0x021101d7` 确定目标静态指令。前端以 FTQ `0/3` 和目标半字偏移 `0xA` 关联取指来源；后端分配后以 ROB `1/16`、物理目的 51 关联本次执行。逻辑源 v2、v1 对应物理源 50、48。

本次 VCD 的时钟周期为 2 ps，偶数 ps 为上升沿。判定 valid/ready 握手时，读取上升沿之前的稳定值，因此许多 Marker 放在事件沿前 1 ps；沿后的数据或 valid 可能已经属于下一条指令。退休则观察 `isCommit && commitValid` 及对应的 ROB/指令标识。这里的 ps 是仿真时间标尺。

![从取指块到已提交映射的指令路径](../assets/stage1/vadd-path-overview.png)

图 3-2　分析路径。前端追踪目标指令所属的取指块，后端追踪操作数就绪、执行、写回和提交过程。

表 3-1 汇总确定的事件沿，以 FTQ 请求接受沿为相对周期零点。它先给出全貌，后文解释各段之间的因果关系。

表 3-1　目标动态指令的主要事件。

| 事件 | VCD 时间 | 相对周期 |
| --- | --- | --- |
| FTQ 取指请求接受 | 5080 ps | 0 |
| ICache 应答与 IFU F2 推进 | 5084 ps | 2 |
| IFU 输出进入 IBuffer | 5086 ps | 3 |
| 后端入口接受，目标进入 decodeBuf | 5088 ps | 4 |
| 译码接受目标 | 5112 ps | 16 |
| 重命名输出接受 | 5116 ps | 18 |
| 派发入队 | 5118 ps | 19 |
| 两个物理源先后就绪 | 5252、5258 ps | 86、89 |
| 发射接口接受 | 5262 ps | 91 |
| 执行单元接受操作数 | 5268 ps | 94 |
| 运算输出握手 | 5270 ps | 95 |
| 物理寄存器写入 | 5272 ps | 96 |
| ROB 退休 | 5274 ps | 97 |
| v3 已提交映射更新 | 5278 ps | 99 |

完整信号层级和源码入口见阶段一附录。正文只保留判定事件所需的字段；完整信号层级名称见附录。

## 3.3 从取指块中找到 VADD

### 3.3.1 FTQ 请求与 ICache 返回数据

5079 ps 时，FTQ 请求的 valid/ready 均为 1，身份为 `0/3`，起始地址为 `0x80000134`。请求在 5080 ps 被接受，沿后接口立即转向 FTQ `0/4`、地址 `0x80000154`。这说明接口能够连续发送取指块；目标指令位于前一块内部，所以它的 PC 可以不同于该块的起始地址。

![FTQ请求身份在接受沿前后发生切换](../assets/stage1/frontend-ftq-marker5080ps.png)

图 3-3　5080 ps 接受 FTQ `0/3` 后，接口转向下一取指块。目标所属请求应读取接受沿之前的 FTQ 编号。

5083 ps，ICache 返回有效应答，地址仍为 `0x80000134`；IFU F2 同时持有 FTQ `0/3`，`f2_fire=1`。本次请求跨越两条缓存行，`doubleline=1`，两侧异常字段均为零。ICache 应答为 Valid 接口，结合对应地址和 IFU 推进条件确认 5084 ps 的交接。

![ICache应答与IFU中的FTQ身份对应](../assets/stage1/frontend-icache-5083ps.png)

图 3-4　ICache 的有效应答与 IFU F2 中的 FTQ `0/3` 对应。

返回总线最低 128 位为 `020661A7_021101D7_0205E107_02056087`，右端是低位。目标机器码位于 `[95:64]`：

表 3-2　返回数据中的四条连续指令。

| 位段 | 地址 | 机器码与操作 |
| --- | --- | --- |
| [31:0] | 0x80000140 | 0x02056087，装载 v1 |
| [63:32] | 0x80000144 | 0x0205e107，装载 v2 |
| [95:64] | 0x80000148 | 0x021101d7，目标 VADD |
| [127:96] | 0x8000014c | 0x020661a7，存储 v3 |

请求起点落在前一缓存行末段；返回总线按选中的 8 字节 bank 重新拼装，本例最低部分来自 `0x80000140`。IFU 先对返回数据复制拼接，再用切分指针选出半字：目标对应 `f2_cut_ptr_10/11=36/37`，映射回原数据的半字 4/5。因此，目标在总线中的位置须按切分指针推算，不能把 PC 与请求起点的差值直接当作总线偏移。

### 3.3.2 IFU 输出和 IBuffer 接收

目标距取指起点 20 字节，即第 10 个半字位置。5085 ps，IFU 位置 10 的 PC、机器码分别为 `0x80000148`、`0x021101d7`，包内 `valid` 和 `enqEnable` 均为 `0xd555`，其 bit10 有效；整包 valid/ready 为 1/1，接收侧没有 flush。目标由此在 5086 ps 进入 IBuffer。

![IFU位置10的指令及有效掩码](../assets/stage1/frontend-ifu-5085ps.png)

图 3-5　IFU 位置 10 的指令身份、包内掩码和接口握手共同确认接收。

到 5087 ps，目标位于 IBuffer 输出槽 5，FTQ 仍为 `0/3`，`ftqOffset=0xA`。IFU 采用半字位置编号，IBuffer 输出采用指令槽编号，因此从位置 10 变成槽 5，只是编号方式不同，仍是同一条指令。

![IBuffer输出可被后端入口接受而译码尚未就绪](../assets/stage1/frontend-ibuffer-5087ps.png)

图 3-6　后端入口 `cfVec5` 的 valid/ready 为 1/1，但译码输入 ready 为 0，指令先由入口缓冲保存。

### 3.3.3 入口接受与译码接受为何相隔十二周期

5088 ps 的后端入口接受并不意味着译码级已经消费目标。当时前两条指令被译码接收，目标从输出槽 5 进入 decodeBuf 槽 3。随后，前方指令继续被消费，目标在 5090、5092 ps 依次移到槽 1、槽 0，PC、机器码和 FTQ 标识保持不变。

![目标在decodeBuf中逐步移到队首](../assets/stage1/frontend-decode-buffer-5093ps.png)

图 3-7　5093 ps 目标位于有效的 decodeBuf 槽 0；这只是缓冲槽位变化，仍是同一条目标指令。

目标到队首后仍需等待译码 ready。5111 ps 的输入 valid/ready 才同时为 1，redirect=0，因此 5112 ps 为真正的译码接受沿。沿后 `decodeBufValid_0` 清零，译码入口转向下一条存储指令 `0x8000014c`。入口 valid 可以继续为 1，因为此时它已经描述下一条指令。

![目标在5112ps被译码接受](../assets/stage1/frontend-decode-accept-5111ps.png)

图 3-8　5111 ps 的稳定握手值确定 5112 ps 的译码接受事件。

## 3.4 从逻辑寄存器到可执行操作

### 3.4.1 译码建立运算和源类型

译码将机器码解释为向量加法：逻辑源为 v2、v1，逻辑目的为 v3，`vecWen=1`、`rfWen=0`；`fuType=0x80000`、`fuOpType=0x40` 对应本版本的向量整数加法路径。向量控制 `vsew=2`、`vlmul=0`、`vm=1`，即 e32/m1 无掩码操作。

![VADD译码控制字段](../assets/stage1/02-decode-5111ps.png)

图 3-9　译码把指令编码转换为逻辑源、目的及执行控制。两个源类型均为向量类型。

汇编按 `vd,vs2,vs1` 排列，而本实现的源 0/1 按 RS1/RS2 字段提取，因此该实例的源 0 对应 v2，源 1 对应 v1。通用 old-vd 字段仍能看到逻辑 v3，但本例 `isDependOldVd=0`，旧目的不参与加法。

### 3.4.2 重命名分配物理版本

5115 ps，重命名输出把 v2、v1 映射到物理源 50、48，为新的 v3 分配物理目的 51，同时携带 ROB `1/16`。valid/ready 为 1/1，输出在 5116 ps 被接受。波形采用十六进制时，这些编号分别显示为 `0x32`、`0x30`、`0x33`，ROB value 为 `0x10`。

![重命名给目标分配ROB和物理目的](../assets/stage1/03-rename-5115ps.png)

图 3-10　重命名后的物理源、物理目的和 ROB 身份，为后端追踪提供共同标识。

分配物理编号是为了区分同一逻辑寄存器的不同版本；源数据何时可读，还取决于写出这些物理寄存器的前序指令何时完成。5117 ps 的派发接口虽然 valid/ready 为 1/1，两个 `srcState` 仍为 0，因此目标在 5118 ps 入队后等待源数据。

![派发成功时源数据仍未就绪](../assets/stage1/04-dispatch-5117ps.png)

图 3-11　目标进入发射队列时两个源尚未就绪。派发 ready 表示发射队列还能接收新条目；操作数是否就绪由 srcState 另行表示。

### 3.4.3 写回唤醒与发射

5251 ps 的有效写回标签为 48，使源 1 在 5252 ps 就绪；5257 ps 的标签为 50，使源 0 在 5258 ps 就绪。到 5259 ps，条目的 `canIssue=1`。队列随后选择该条目，5261 ps 的发射接口 valid/ready 为 1/1，携带 ROB `1/16`、pdest 51 和两个物理读地址 50、48，于 5262 ps 接受。

由此可以解释表 3-1 中较长的等待区间：这次动态执行的大部分时间花在等待源就绪和调度入发射上。因此，指令端到端周期与执行单元计算延迟需要分开看。

## 3.5 计算结果怎样成为架构状态

### 3.5.1 实际操作数与计算完成

5267 ps，父执行单元 EXU2 的入口握手有效，ROB/pdest 与此前相同。两个 128 位源按 32 位分组为：

```text
src0 = 00000028_0000001e_00000014_0000000a
src1 = 00000004_00000003_00000002_00000001
VL   = 4
```

右端为元素 0，因此它们分别是 B 和 A。5268 ps 接受输入后，5269 ps 的 `VialuFix` 输出已经携带完整和，输出 valid/ready 为 1/1，5270 ps 完成握手。

![执行入口的实际操作数与身份](../assets/stage1/05-execution-input-5267ps.png)

图 3-12　5268 ps 接受的操作数为两组四元素向量，ROB `1/16` 和 pdest 51 与重命名一致。

![VADD完整128位结果](../assets/stage1/06-execution-output-5269ps.png)

图 3-13　5270 ps 输出的 128 位结果为 `0x0000002c00000021000000160000000b`，对应 `[11,22,33,44]`。

### 3.5.2 物理写入、退休和映射更新

运算输出经写回数据通路送到向量寄存器堆。5271 ps 写口 `wen=1`、地址为 51，5272 ps 四个 32 位分片的 `mem_51` 分别写入 `0x0b`、`0x16`、`0x21`、`0x2c`。此时结果已经存在于物理寄存器中。

![物理寄存器51的四个分片写入结果](../assets/stage1/07-physical-write-marker5274ps.png)

图 3-14　物理写入发生于 5272 ps，图中 Marker=5274 ps 时各分片保持新值。

随后，5273 ps 的 ROB 退休槽 0 满足 `isCommit=commitValid_0=1`，PC、机器码、ROB `1/16` 和 pdest 51 均匹配目标，指令在 5274 ps 按序退休。这一步确认该结果已按程序次序提交。

![ROB确认目标指令有效退休](../assets/stage1/08-rob-before-5273ps.png)

图 3-15　5273 ps 的有效退休槽确认 5274 ps 退休事件。

退休信息再经 RAB 更新向量已提交映射。5277 ps，映射写口准备把逻辑 v3 指向物理 51，`arch_table_3` 尚为旧编号 3；5278 ps 沿后，表项变为 51。

![提交映射更新前的旧表项](../assets/stage1/09-map-before-5277ps.png)

图 3-16　5277 ps 的写口为 addr=3、data=51，已提交表项仍为旧编号 3。

![提交映射更新后的新表项](../assets/stage1/10-map-after-5278ps.png)

图 3-17　5278 ps 后 v3 的已提交映射指向物理寄存器 51。

这三个时刻承担不同职责：5272 ps 保存计算数据，5274 ps 确认按序退休，5278 ps 更新已提交的寄存器版本。映射表保存的是物理编号，128 位运算结果早已写入对应寄存器。把这三步分开观察后，就能从 FTQ 取指请求、经 ROB 与物理寄存器编号，一直追到最终的已提交映射，说明这一次 VADD 如何完成。

本章观察的是指定 e32/m1/VL4 实例。观测从前端 FTQ 请求起，经后端源依赖等待，到提交更新为止；缓存缺失处理、BPU 内部预测及其他向量配置未纳入本次观测。复现材料与完整信号索引集中于阶段一附录。
