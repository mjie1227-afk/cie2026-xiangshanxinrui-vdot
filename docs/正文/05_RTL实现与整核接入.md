# 5 RTL 实现与整核接入

本章围绕五类关键改动展开：DecodeUnit 译码、FuConfig 配置、VDot 算术模块、ROB 中的 mtval 编码表和 CSR 选择器。完整接入还涉及指令模式、向量分类、FuType、执行拓扑和异常信息 Bundle；这些修改均包含在交付补丁中。本章按“译码 → 功能单元配置 → 算术和控制 → ROB/CSR”的顺序说明，对应赛题 2.2。

把点积公式写成算术模块只是接入的第一步。香山还需要知道指令属于哪种执行类型、读取哪些物理源、何时产生结果，以及异常时怎样保留故障身份。

源码以锁定的香山基版本叠加 VDot 及 mtval 修复补丁为准。下文为保存源码中的关键摘录，完整文件与补丁见阶段二复现索引。

## 5.1 DecodeUnit：单微操作与 oldVd 依赖

DecodeUnit 把 vdot.vv 译成一个微操作、一次目的更新，并声明 oldVd 依赖。

custom-0 位型被识别后，指令仍进入向量分类和权限检查通路。DecodeUnit 的设置如下：

```scala
  when(inst.isVdot) {
    io.deq.isComplex := true.B
    io.deq.uopInfo.numOfUop := 1.U
    io.deq.uopInfo.numOfWB := 1.U
    io.deq.uopInfo.lmul := 1.U
  }
```

`isComplex` 表示走相应的向量译码路径，`numOfUop=1` 让八项计算由同一个微操作完成。这里的 `uopInfo.lmul` 是内部微操作信息；向量类型中 LMUL=1 的编码则是 `vtype.vlmul=0`。

我们还在 `isDependOldVd` 条件中加入了 `inst.isVdot`，让调度端保留旧目的依赖。合法 VL=0 由此能把旧物理目的中的完整值复制到新物理目的，见第 4 章。oldVd 虽然不参与点积运算，仍需声明为源依赖，VL=0 时才能读到旧值。完整译码修改见 DecodeUnit 源码[〔4〕](../../src/XiangShan/src/main/scala/xiangshan/backend/decode/DecodeUnit.scala)。

## 5.2 FuConfig：把 VDot 挂入 VFEX0

`VdotCfg` 声明五组输入、固定两拍延迟和 128 位输出，VDot 由此挂入 VFEX0。

新增的 `FuType.vdot` 区分执行类型。执行拓扑把 VDot 挂入 VFEX0，`VdotCfg` 声明输入、延迟和输出能力：

```scala
  val VdotCfg = FuConfig (
    name = "vdot",
    fuType = FuType.vdot,
    fuGen = (p: Parameters, cfg: FuConfig) => Module(new VDot(cfg)(p)),
    srcData = Seq(Seq(VecData(), VecData(), VecData(), V0Data(), VlData())),
    piped = true,
    writeVecRf = true,
    writeV0Rf = true,
    latency = CertainLatency(2),
    vconfigWakeUp = true,
    maskWakeUp = true,
    destDataBits = 128,
    exceptionOut = Seq(illegalInstr),
  )
```

三组 `VecData()` 对应两个源和 oldVd，`V0Data()` 和 `VlData()` 提供掩码与长度信息。掩码与配置唤醒属性让指令等待正确版本的控制数据。`writeV0Rf` 支持 vd=v0，`destDataBits=128` 与完整目的布局一致。固定两拍延迟既规定了执行模块的流水级数，也让后端按两拍安排结果唤醒和写回。

这份配置决定算术模块的输入来源和结果写回方式。完整定义见 FuConfig 源码[〔5〕](../../src/XiangShan/src/main/scala/xiangshan/backend/fu/FuConfig.scala)。

## 5.3 VDot 模块：有符号乘法、+& 归约与 S1/S2 寄存器

VDot 模块的算术主体逐行对应第 4 章的数据通路：三级 `+&` 依次得到 17、18、19 位结果，S1、S2 两个寄存器划出两拍流水。

VDot 继承既有的 `VecPipedFuncUnit`，模块展开时检查 VLEN、结果宽度和延迟设置：

```scala
class VDot(cfg: FuConfig)(implicit p: Parameters) extends VecPipedFuncUnit(cfg) {
  require(VLEN == 128 && cfg.destDataBits == 128)
  require(latency == 2 && latdiff == 0)
```

算术主体如下：

```scala
  val products = VecInit((0 until 8).map { i =>
    val product = vs1(8*i+7, 8*i).asSInt * vs2(8*i+7, 8*i).asSInt
    Mux(srcMask(i), product, 0.S(16.W))
  })
  val p1 = S1Reg(products)
  val pairs = (0 until 4).map(i => p1(2*i) +& p1(2*i+1))
  val halves = (0 until 2).map(i => pairs(2*i) +& pairs(2*i+1))
  val sum = halves(0) +& halves(1) // 19 bits, including +131072
  val result = S2Reg(Cat(0.U(96.W), sum.pad(32).asUInt))
```

字节切片后的 `.asSInt` 保证 0x80 按 −128 参与乘法。掩码筛选发生在 S1 之前，屏蔽项为 16 位有符号零。每次 `+&` 都保留额外进位，三级结果依次为 17、18、19 位。`sum.pad(32)` 把有符号和扩展到 32 位，`Cat` 再拼接高 96 位零。负结果只在低 32 位带符号，不会污染高位。

`S1Reg`、`S2Reg` 让乘积与格式化结果分别跨过流水边界。输出的有效位、ROB 身份和控制信息由父类与末级逻辑同步传递，与结果数据处于同一拍。完整模块见 VDot.scala[〔6〕](../../src/XiangShan/src/main/scala/xiangshan/backend/fu/wrapper/VDot.scala)。

## 5.4 末级：结果选择、非法检查与 redirect 取消

末级分别处理数据选择与异常标记：合法非零 VL 输出 S2 结果，合法 VL=0 或局部非法配置时数据选择 oldVd；非法配置另置 `illegalInstr` 并由精确异常路径阻止架构目的更新。被较老 redirect 覆盖的指令不产生有效输出。

末级检查执行时携带的向量配置，选择普通结果或旧目的，并把局部非法条件交给精确异常通路：

```scala
  val illegal = outVecCtrl.vill || outVecCtrl.vsew =/= 0.U ||
    outVecCtrl.vlmul =/= 0.U || outVstart =/= 0.U ||
    (outVl =/= 0.U && (outVl < 8.U || outVl > 16.U))
  io.out.bits.res.data := Mux(outVl === 0.U || illegal, outOldVd, result)
  io.out.bits.ctrl.exceptionVec.get(illegalInstr) := illegal
  // Keep vecWen/v0Wen for legal vl=0: the new physical destination needs oldVd.
  // CSR updates and precise exceptions remain on the ordinary commit path.
  io.out.valid := fixValidVec.last && !outCtrl.robIdx.needFlush(io.flush)
```

向量权限和部分类型检查位于上游，这里保留的是 FU 局部保护。

`io.out.valid` 同时要求末级有效、且未被较老 redirect 覆盖。ROB 指针中的 flag/value 区分环形队列的位置与代际。`needFlush` 据此判断本指令是否比发生跳转的分支更年轻、需要被取消。若结果已物理写入后才收到较老分支恢复，ROB 和重命名恢复会阻止它退休。因此，验证时分别观察物理寄存器写入和最终的架构状态更新。

向量脏状态（VS=Dirty）请求由同一拍各退休槽的标记汇总得到：

```text
VS-dirty 请求来源 = isCommit AND OR(commitValid[i] AND dirtyVs[i])
```

无效退休槽即使残留 dirtyVs=1，也不参与聚合。各退休槽标记、ROB 注册请求与 CSR 接收请求之间的对应关系，用正常和取消两个实例检查，见第 6 章。

## 5.5 mtval 修复：ROB 保存编码字段，队首重建指令字

执行期非法异常现在也能把故障指令字写入 mtval：ROB 在分配时保存 VDot 的可变编码字段和代际，队首异常时重建指令字，再由 CSR 选择器优先接收。下面按现象、原因、改法、回归四步说明。

**现象：DUT 的 mtval 为零**　协同仿真中，短 VL 用例 short-1-vm0 由执行单元判为非法指令异常。参考模型的 mtval 为故障机器码 `0x0020818b`，DUT 的 mtval 为零。

**原因：执行期非法异常拿不到指令字**　原有 trapInstInfo 通路主要服务于译码期非法指令异常。VDot 的短 VL 非法条件在执行期才产生，指令到达 ROB 队首时找不回自己的编码。

**改法：ROB 分配时保存可变编码字段和代际，队首重建指令字**　新增表的核心源码如下：

```scala
  val isVdot = RegInit(VecInit(Seq.fill(RobSize)(false.B)))
  val generation = Reg(Vec(RobSize, Bool()))
  val fields = Reg(Vec(RobSize, UInt(16.W)))
  for (a <- io.alloc) {
    when(a.valid) {
      val idx = a.bits.robIdx.value
      isVdot(idx) := VdotInstructions.VDOT_VV === a.bits.instr
      generation(idx) := a.bits.robIdx.flag
      fields(idx) := Cat(a.bits.instr(25), a.bits.instr(24,20),
                        a.bits.instr(19,15), a.bits.instr(11,7))
    }
  }
  val f = fields(io.head.value)
  val word = Cat(0.U(6.W), f(15), f(14,10), f(9,5), 0.U(3.W), f(4,0), "h0b".U(7.W))
  val matched = isVdot(io.head.value) && generation(io.head.value) === io.head.flag
  // Same one-cycle capture as Rob.io.exception; no writeback-order arbitration.
  io.out.valid := RegNext(io.trap && io.illegal && !io.interrupt && matched, false.B)
  io.out.bits := RegEnable(word, io.trap)
```

`vm`、`vs2`、`vs1`、`vd` 共 16 个可变位，加一个类型位和一个代际位，每槽 18 位；48 槽共 864 个存储字段位。固定的 funct6、funct3 和 opcode 可在异常时重建，无需逐槽保存完整的 32 位指令字。以上为字段容量估算，综合面积另需实测。

队首发生非法指令异常时，`matched` 确认类型和代际，`!interrupt` 排除中断，匹配信息随后与 ROB 异常信息同步寄存。CSR 用选择器优先接收该信息，其他异常保留原有通路：

```scala
  csrMod.io.trapInst := xiangshan.backend.rob.VdotTrapInstSelect(
    csrIn.exception.valid, csrIn.exception.bits.isInterrupt,
    csrIn.exception.bits.exceptionVec(EX_II), csrIn.exception.bits.vdotTrapInst,
    trapInstMod.io.currentTrapInst)
```

整条路径为“分配时保存 → 队首异常匹配 → 重建指令字 → CSR 选择”。它按精确异常身份取值，不依赖各功能单元完成的先后顺序。源码入口为 VdotTrapInst.scala 和 CSR.scala[〔7〕](../../src/XiangShan/src/main/scala/xiangshan/backend/rob/VdotTrapInst.scala)[〔8〕](../../src/XiangShan/src/main/scala/xiangshan/backend/fu/wrapper/CSR.scala)。

**回归：原异常用例 64 例 EXCEPTION 全部通过**　修复版 emu 用原异常用例回归，64 例 EXCEPTION 全部通过，RTL 与参考模型的 mtval 一致。失败读数、故障 PC 和回归记录见第 7 章。

## 5.6 补丁、emu、参考库与测试镜像的对应关系

RTL 仿真器、NEMU 参考库和测试镜像分别编译，运行时配合使用。复现时需要对应的源码版本、补丁和二进制文件校验值。

译码、配置、VDot、ROB 和 CSR 修改共同进入 Chisel 展开和 emu 构建。NEMU 语义独立生成参考共享库，测试应用独立生成 RISC-V 镜像。

最终补丁已包含首版接入和异常指令字修复，见完整交付补丁[〔9〕](../../evidence/records/artifacts/vdot-mtval-fix-2026-10-24/delivery-v2)。后续功能、等价和性能实验复用锁定的修复版 emu 与源码 NEMU；只调整应用时，仿真器和参考库无需重新编译。下一章先用基础输入检查算术与布局，再用代表性波形检查它们在后端中的实际行为。
