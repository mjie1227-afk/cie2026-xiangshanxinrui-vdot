# 7 NEMU 扩展与差分验证

本项目已在 NEMU 中加入 vdot.vv 的译码和执行语义，并完成参考库接口检查与 RTL/NEMU 整核协同验证。参考模型 API 通过 268 例，另有 10 例因配置不适用单列；修复版整核的 SMOKE、EXCEPTION、OVERLAP 和 PIPELINE 套件全部通过。

验证分三步配合进行。应用自检把输出与独立算出的答案比较；DiffTest 在同步点比较 RTL 与 NEMU 的寄存器和相关状态；波形则记录指令何时执行、发生异常、取消或退休。RTL 和 NEMU 分别按同一份指令规格实现，既核对点积答案，也核对异常与状态更新。

本章对应赛题 3.1.1 和 3.1.2，说明参考模型实现、构建与加载关系、验证结果，以及短 VL 异常中 mtval 失配的定位过程。

## 7.1 NEMU 与 RTL 共用 v0.1 指令规格

参考模型与 RTL 遵循同一份项目 v0.1 指令规格，合法配置范围和状态更新规则一致〔1〕。

在向量执行权限可用的前提下，合法配置要求 vill=0、SEW=8、LMUL=1、vstart=0，VL 为 0 或 8～16，vtype 保留高位为零。合法非零 VL 固定计算源低八项，精确和写入低 32 位、高 96 位清零；合法 VL=0 保持完整旧目的。类型、权限和重启条件的检查排在长度分支之前。

RTL 基于 XiangShan 16ae9ddc，叠加 VDot 和异常修复；参考模型基于 NEMU a48a11f2，叠加独立的语义实现。完整版本和二进制文件校验值见阶段三复现索引。

## 7.2 custom-0 译码规则与 def_EHelper(vdot)

NEMU 的改动包括译码入口、执行 ID 注册、头文件接入和新增语义函数。custom-0 的末七位为 `0001011`，funct6 和 funct3 为零，其余字段解析 vm 及寄存器编号。译码规则如下：

```c
#ifdef CONFIG_RVV
  def_INSTR_IDTAB("000000 ? ????? ????? 000 ????? 00010 11", OP_V  , vdot);
  def_INSTR_IDTAB("??????? ????? ????? ??? ????? 10101 ??", OP_V  , OP_V);
#endif // CONFIG_RVV
```

第一条规则匹配 custom-0 编码，告诉 NEMU 执行 vdot；第二条保留原有的标准 OP-V 处理。新增执行 ID 注册在 isa-all-instr.h，vcompute.h 引入 vdot.h。这样，NEMU 识别机器码后，就能调用 `def_EHelper(vdot)` 执行对应规则。

执行函数如下，摘自 vdot.h 源码[〔2〕](<../../src/NEMU/src/isa/riscv64/instr/rvv/vdot.h>)：

```c
def_EHelper(vdot) {
  require_vector(true); // host/guest VS and vill, before the vl=0 path
  if ((vtype->val >> 8) != 0 || vtype->vsew != 0 || vtype->vlmul != 0 ||
      vstart->val != 0 || (vl->val != 0 && (vl->val < 8 || vl->val > 16))) {
    longjmp_exception(EX_II);
  }
  const uint32_t word = s->isa.instr.val;
  const unsigned vd = (word >> 7) & 31;
  const unsigned vs1 = (word >> 15) & 31;
  const unsigned vs2 = (word >> 20) & 31;
  const unsigned vm = (word >> 25) & 1;
  if (vl->val != 0) {
    // Snapshot before any write, including vd=v0 and all source overlaps.
    const uint64_t a = cpu.vr[vs1]._64[0];
    const uint64_t b = cpu.vr[vs2]._64[0];
    const uint64_t mask = cpu.vr[0]._64[0];
    int32_t sum = 0;
    for (unsigned i = 0; i < 8; ++i) {
      const int ai = ((int)((a >> (8*i)) & 255) ^ 128) - 128;
      const int bi = ((int)((b >> (8*i)) & 255) ^ 128) - 128;
      if (vm || ((mask >> i) & 1)) sum += ai * bi;
    }
    cpu.vr[vd]._64[0] = (uint32_t)sum;
    cpu.vr[vd]._64[1] = 0;
  }
  vstart->val = 0;
  vp_set_dirty(); // includes legal vl=0 and guest VS when virtualized
}
```

实现中有三处与边界测试直接相关：

- 合法性检查位于 VL=0 之前，空操作也不能绕过异常条件。
- 两个源和掩码先存入局部变量，再改写目的；vd 与源或 v0 重叠时仍读取旧值。
- `(uint32_t)sum` 写入低 64 位容器时高 32 位为零，另一个 64 位字也置零，恰好形成低 32 位结果与高 96 位零。

合法 VL=0 跳过目的更新，但仍执行成功路径的状态处理；`vp_set_dirty()` 复用 NEMU 已有的向量状态机制。源文件及译码入口统一保存在 NEMU 修改快照中[〔3〕](<../../src/NEMU>)。

## 7.3 仿真器、参考库与测试镜像的构建和加载

协同仿真要准备三个文件：`emu` 模拟香山硬件，`riscv64-nemu-interpreter-so` 提供 NEMU 参考模型，RISC-V 测试镜像保存待运行程序。启动时，emu 加载测试镜像，`--diff` 指向参考库，`-F` 指向启动 Flash。程序在硬件模型和参考模型中执行，DiffTest 在同步点比较两侧的架构状态。

![独立期望与架构状态差分的关系](<../assets/technical/co-verification.svg>)

图 7-1　验证结构。应用对照独立期望值；DiffTest 在退休、异常等同步点比较 RTL 与 NEMU 导出的架构状态。

DiffTest 通过 regcpy 在两侧传递状态。本配置的状态交换区共 1400 字节，其中向量寄存器区从第 800 字节开始，占 512 字节，对应 32 个 128 位寄存器。参考库 API 测试先写入指定状态，执行一条指令，再读回比较；整核测试则让真实程序驱动 RTL 与 NEMU，检查完整执行过程[〔4〕](<../../evidence/records/artifacts/scnet-abi-2026-10-24/abi-review.json>)。

验收同时查看参考库路径、DiffTest 启用、应用 PASS、GOOD TRAP 和被测程序退出码；脚本及日志收集的退出状态单列记录。完整构建与运行命令入口见交付与复现记录〔5〕。

## 7.4 API 268 例与整核四类套件

API 测试先给 NEMU 设置寄存器和 CSR 初值，再让它执行一条 VDot，最后读回 32 个向量寄存器及相关 CSR，与预期比较。它检查参考模型自身的行为；随后运行整核套件，检查 RTL 是否得到同样的结果。表 7-1 列出 API 测试的数量。

表 7-1　参考模型 API 检查

| 类别 | 数量 | 主要检查 |
| --- | --- | --- |
| 合法非零 VL | 93 | 目的结果及状态更新 |
| 合法 VL=0 | 40 | 完整旧目的保持及状态策略 |
| 非法配置 | 135 | 异常与相关状态保持 |
| 通过合计 | 268 | 上述三类 |
| 配置不适用 | 10 | 本参考库构建无法通过软件动态关闭 misa.V，单列 |

API 层使用的本地参考库与服务器参考库身份分别保存。十个不适用用例不计入通过数，原因在于参考库的 RVV 构建配置。每例记录见原始 API 结果[〔6〕](<../../evidence/records/artifacts/vdot-integration-2026-10-24/nemu-api-151012/result.json>)。

整核阶段再检查译码、执行、异常和退休的联合行为。表 7-2 统一列出定向套件；PIPELINE 小计为三项流水套件之和。

表 7-2　修复版整核差分套件

| 套件 | 用例数 | 目的 | 结果 |
| --- | --- | --- | --- |
| SMOKE | 7 | 正负数、极值、掩码、VL=0/16、完整目的与状态 | 通过 |
| EXCEPTION | 64 | 62 个预期陷阱、2 个合法对照；cause、mepc、mtval | 通过 |
| OVERLAP | 60 | 15 种源、目的、掩码相等关系 | 通过 |
| PIPELINE-DEPS | 48 | 12 个依赖测试程序 | 通过 |
| PIPELINE-MIXED | 32 | 8 个混发测试程序 | 通过 |
| PIPELINE-CANCEL-CSR | 40 | 32 个分支场景、8 个精确异常场景 | 通过 |
| PIPELINE 小计 | 120 | 上述三项流水套件 | 通过 |

Hello 与 VADD 在修复后同轮通过。等价及性能应用另行运行，其内核调用数按各自实验统计。上述整核定向结果来自修复回归与流水回归原始记录[〔7〕](<../../evidence/records/artifacts/vdot-mtval-fix-2026-10-24/server-xYGYlZ/review.json>)[〔8〕](<../../evidence/records/artifacts/vdot-pipeline-2026-10-24/server-JuGUz6/review.json>)。

## 7.5 执行期非法异常的 mtval 失配与修复

短 VL 用例曾发现一个异常信息错误：RTL 正确报告了非法指令，却没有把故障机器码写入 mtval。NEMU 的 mtval 有正确编码，因此 DiffTest 能报出差异。补上机器码传递通路后，原来的 64 个异常用例全部通过。下面按现象、原因、修改和复测说明。

### 7.5.1 现象：DUT 的 mtval 为零

早期 emu 执行短 VL 用例 short-1-vm0 时，短 VL 按规格触发非法指令异常，但 DiffTest 报告：

```text
mtval different at pc = 0x0080000218, right=0x0020818b, wrong=0
```

参考模型的 mtval 为故障机器码 `0x0020818b`，DUT 的 mtval 为零。结合反汇编和提交轨迹可以区分两个 PC：`0x80000218` 是前一条已提交的 `sd t0,40(s0)`，实际发生异常的 VDot 位于 `0x8000021c`。异常同步时，差分行保留最近的比较位置，`mepc=0x8000021c` 则精确记录了故障指令地址。

![参考模型记录故障指令地址和指令字](<../assets/stage2/mtval-before-reference.png>)

图 7-2　参考快照为 mcause=2、mepc=0x8000021c、mtval=0x0020818b。

![DiffTest发现DUT与参考mtval不同](<../assets/stage2/mtval-before-difference.png>)

图 7-3　DUT 的 mtval 为零，参考值为故障机器码，差分检查随后中止运行。

### 7.5.2 原因：执行期非法异常拿不到指令字

VL=1 的非法条件是在执行期判断出来的。原有 trapInstInfo 主要传递译码期发现的非法指令，VDot 到达 ROB 队首时，异常类型已经送到，匹配的机器码却没有跟上，因此 mtval 读到零。需要修复的是故障指令信息通路。

### 7.5.3 改法：ROB 分配时保存可变编码字段和代际，队首重建指令字

修复后，ROB 在分配槽位时保存 VDot 的可变编码字段和代际。发生队首异常时，先确认槽位中的记录属于本次指令，再拼回机器码，交给 CSR 选择器。异常仲裁和 NEMU 语义保持原样，新增通路补上执行期异常所需的指令字。字段组成和容量见第 5 章 5.5。

### 7.5.4 回归：原异常用例 64 例 EXCEPTION 全部通过

修复生成新 emu 后，我们用原异常镜像与参考库配置回归：64 例 EXCEPTION 全部通过，随后 OVERLAP、SMOKE、Hello 与 VADD 也通过。原失败 emu 和日志保留用于追溯，成功结果对应修复后的仿真器版本。

![异常修复后的回归通过记录](<../assets/stage2/exception-regression.png>)

图 7-4　修复后异常套件正常结束，应用 PASS、GOOD TRAP 和退出状态共同确认本次回归结果。

该回归保留了失败快照、故障指令定位、RTL 修复和原用例复测记录。诊断与反汇编依据见差分诊断记录，具体修改见修复说明〔9〕〔10〕。

## 7.6 OVERLAP 与 PIPELINE 的运行记录

OVERLAP 专门让目的与源或掩码使用同一寄存器编号，检查计算是否仍读取执行前的旧值。PIPELINE-DEPS 检查后续指令使用前一条结果时的依赖；MIXED 检查与其他向量指令交错执行；CANCEL-CSR 检查分支取消和精确异常。下列日志与表 7-2 对应，内部时间关系见第 6 章波形。

![寄存器重叠套件运行结果](<../assets/stage2/overlap-regression.png>)

图 7-5　OVERLAP 套件通过，保留 DiffTest、GOOD TRAP 及退出记录。

![依赖测试运行结果](<../assets/stage2/pipeline-dependencies.png>)

图 7-6　PIPELINE-DEPS 的依赖程序汇总与正常结束记录。

![混发测试运行结果](<../assets/stage2/pipeline-mixed.png>)

图 7-7　PIPELINE-MIXED 检查选定混发场景的架构结果。

![分支取消和精确异常场景运行结果](<../assets/stage2/pipeline-branch-csr.png>)

图 7-8　PIPELINE-CANCEL-CSR 分别记录分支和精确异常场景。

这些记录表明，定向套件中的 RTL 与参考模型架构状态一致。第 8 章据此构造标准 RVV 组合，并检查三条路径在统一调用约定下的完整结果和状态，为性能比较准备基线。
