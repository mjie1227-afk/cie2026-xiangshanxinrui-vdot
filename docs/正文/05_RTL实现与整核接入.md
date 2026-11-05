# 5 RTL 实现与整核接入

接入 VDot，需要让处理器能认出指令、读到正确输入、送到新的计算单元，并把结果或异常交回后端。本章沿这条顺序说明 DecodeUnit、FuConfig、VDot 和 ROB/CSR 的修改。指令编码、向量分类、FuType、执行拓扑和异常 Bundle 的完整修改保存在交付源码与补丁中。

算术单元收到输入后能算出正确答案，还需要后端配合：输入未就绪时等待，完成时唤醒使用结果的指令，遇到异常或分支取消时停止提交。执行类型、源依赖、固定延迟和 ROB 编号就是这些配合所需的信息。

源码以锁定的香山基版本叠加 VDot 及 mtval 修复补丁为准。下文为保存源码中的关键摘录，完整文件与补丁见阶段二复现索引。

## 5.1 DecodeUnit：单微操作与 oldVd 依赖

custom-0 位型被识别后，指令仍进入向量分类和权限检查通路。DecodeUnit 的设置如下：

```scala
  when(inst.isVdot) {
    io.deq.isComplex := true.B
    io.deq.uopInfo.numOfUop := 1.U
    io.deq.uopInfo.numOfWB := 1.U
    io.deq.uopInfo.lmul := 1.U
  }
```

`isComplex` 使 VDot 进入对应的向量译码路径；`numOfUop=1` 规定八项点积只生成一个微操作，`numOfWB=1` 规定一次目的更新。`uopInfo.lmul` 是内部字段，不能直接当作软件 vtype 的编码；软件设置 LMUL=1 时，`vtype.vlmul` 的编码为 0。

`isDependOldVd` 加入 `inst.isVdot` 后，调度端知道 VDot 还要读取目的旧值。旧值未就绪时，指令会等待；旧值就绪后，合法 VL=0 可以把它复制到新物理目的。非零 VL 的点积仍从零开始求和[〔4〕](<../../src/XiangShan/src/main/scala/xiangshan/backend/decode/DecodeUnit.scala>)。

## 5.2 FuConfig：把 VDot 挂入 VFEX0

`FuType.vdot` 标识新增执行类型，执行拓扑将对应 `VdotCfg` 配置挂入 VFEX0。配置列明输入类型、两拍固定延迟和结果写回能力：

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

前三个 `VecData()` 分别提供两个向量源和 oldVd，`V0Data()` 提供掩码，`VlData()` 提供长度。`maskWakeUp` 和 `vconfigWakeUp` 让后端等正确的掩码与配置就绪后再发射。`writeV0Rf` 支持把 v0 作为目的，`destDataBits=128` 规定写回完整向量。`CertainLatency(2)` 则告诉后端：功能单元按两拍产生结果，唤醒与写回安排需要与之匹配。

这份配置决定算术模块的输入来源和结果写回方式。完整定义见 FuConfig 源码[〔5〕](<../../src/XiangShan/src/main/scala/xiangshan/backend/fu/FuConfig.scala>)。

## 5.3 VDot 模块：有符号乘法、+& 归约与 S1/S2 寄存器

VDot 继承 `VecPipedFuncUnit`，使用父类提供的流水控制。模块展开时先检查向量宽度、结果宽度及两拍延迟约束：

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

`.asSInt` 把取出的字节当作有符号数，例如 `0x80` 按 −128 参与乘法。掩码未选中的乘积在进入 S1 前替换成 16 位零。`+&` 在相加后多保留一位，所以三级结果依次为 17、18、19 位。`sum.pad(32)` 将符号位扩展到 32 位，`Cat` 再在高位拼接 96 个零。

`S1Reg` 保存第一拍的八个乘积，`S2Reg` 保存第二拍整理好的结果。有效位、ROB 编号和控制信息与数据一起推进，因此末级既知道算出了什么，也知道结果应交给哪条指令[〔6〕](<../../src/XiangShan/src/main/scala/xiangshan/backend/fu/wrapper/VDot.scala>)。

## 5.4 末级：结果选择、非法检查与 redirect 取消

末级先检查类型、vstart 和 VL。合法非零 VL 输出 S2 点积结果；VL=0 输出 oldVd；局部检查发现非法配置时，也选择 oldVd，并同时置起 `illegalInstr`。ROB 根据异常位进入精确异常处理。输出是否有效，还要看该指令有没有被 redirect 取消。

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

`io.out.valid` 要求末级有有效指令，且 `needFlush` 没有判定它需要取消。ROB 指针的 value 表示槽位，flag 用于区分队列绕回后的代际；比较完整指针，才能判断 VDot 是否位于发出 redirect 的较早分支之后。若 redirect 到来前已经写回，ROB 和重命名恢复会阻止该结果提交。因此，波形分别记录“写进物理寄存器”和“按序退休”两个时刻。

向量脏状态（VS=Dirty）请求由同一拍各退休槽的标记汇总得到：

```text
VS-dirty 请求来源 = isCommit AND OR(commitValid[i] AND dirtyVs[i])
```

只有 `isCommit` 和对应槽的 `commitValid` 同时有效，该槽的 `dirtyVs` 才计入请求。槽里即使残留 `dirtyVs=1`，只要 `commitValid=0` 就不参与。第 6 章分别用正常退休和分支取消的波形核对这一过程。

## 5.5 mtval 修复：ROB 保存编码字段，队首重建指令字

VL=1～7 等非法条件要到执行期才能判定。异常发生后，CSR 的 mtval 需要保存故障指令的机器码。为使指令到达 ROB 队首时仍能取到该编码，新增表格在 ROB 分配时记下 VDot 的可变字段，到队首异常时再拼回完整指令字。

协同仿真曾在 short-1-vm0 用例中发现 mtval 失配：参考值为 `0x0020818b`，DUT 为零。原 trapInstInfo 主要服务于译码期非法异常，执行期触发的 VDot 到达队首时缺少相应指令字。完整诊断过程见第 7 章。

新增编码表按 ROB 槽保存类型、代际和可变字段，核心实现如下：

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

指令分配 ROB 槽位时先保存编码字段；到队首发生非法异常时，核对类型和代际；匹配后重建 32 位指令字，再交给 CSR 写入 mtval。取值依据是发生异常的 ROB 实例，因此不受各功能单元谁先算完的影响[〔7〕](<../../src/XiangShan/src/main/scala/xiangshan/backend/rob/VdotTrapInst.scala>)[〔8〕](<../../src/XiangShan/src/main/scala/xiangshan/backend/fu/wrapper/CSR.scala>)。

![执行期异常的指令字恢复路径](<../assets/technical/mtval-recovery.svg>)

图 5-1　mtval 修复的数据路径。ROB 分配时保存可变编码字段与代际，队首异常时重建指令字，并与异常信息同步送至 CSR。

修复版 emu 使用原异常用例回归，64 例 EXCEPTION 全部通过，RTL 与参考模型的 mtval 一致。故障 PC、失败快照和回归记录见第 7 章。

## 5.6 补丁、emu、参考库与测试镜像的对应关系

复现时分别构建 RTL 仿真器、NEMU 参考库及 RISC-V 测试镜像，再按保存的版本与配置组合运行。三者的源码、补丁和文件校验值见阶段二附录。

完整交付补丁已包含 VDot 接入与 mtval 修复。后续功能、等价和性能实验复用锁定的修复版 emu 与源码 NEMU；仅调整测试输入或程序时，重新编译应用即可[〔9〕](<../../evidence/records/artifacts/vdot-mtval-fix-2026-10-24/delivery-v2>)。
