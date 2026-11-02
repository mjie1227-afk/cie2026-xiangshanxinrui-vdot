package xiangshan.backend.fu

import chisel3._
import chisel3.util._
import chiseltest._
import chiseltest.simulator.VerilatorCFlags
import firrtl2.options.TargetDirAnnotation
import org.chipsalliance.cde.config.Parameters
import org.scalatest.flatspec.AnyFlatSpec
import top.MinimalConfig
import xiangshan._
import xiangshan.backend.decode.{DecodeUnit, VecExceptionGen, VdotInstructions}
import xiangshan.backend.fu.wrapper.VDot

/** Supplies the ctrl/data/valid pipeline normally supplied by ExeUnit.
  * This harness checks the real FU, not a whole scheduler/writeback/ROB. */
class VDotLocalHarness(implicit p: Parameters) extends Module {
  val cfg = FuConfig.VdotCfg
  val io = IO(new Bundle {
    val valid = Input(Bool())
    val a = Input(Vec(2, UInt(64.W))); val b = Input(Vec(2, UInt(64.W)))
    val old = Input(Vec(2, UInt(64.W))); val mask = Input(Vec(2, UInt(64.W)))
    val vl = Input(UInt(8.W)); val vm = Input(Bool())
    val sew = Input(UInt(3.W)); val lmul = Input(UInt(3.W))
    val start = Input(UInt(8.W)); val vill = Input(Bool())
    val tag = Input(UInt(16.W)); val flag = Input(Bool())
    val kill = Input(Bool()); val killTag = Input(UInt(16.W))
    val killFlag = Input(Bool()); val killSelf = Input(Bool())
    val outValid = Output(Bool()); val result = Output(Vec(2, UInt(64.W)))
    val illegal = Output(Bool()); val outTag = Output(UInt(16.W))
    val outFlag = Output(Bool()); val wen = Output(Bool())
  })
  val dut = Module(new VDot(cfg))
  dut.io.in.bits := 0.U.asTypeOf(dut.io.in.bits)
  dut.io.in.valid := io.valid
  dut.io.out.ready := true.B
  dut.io.flush.bits := 0.U.asTypeOf(dut.io.flush.bits)
  dut.io.flush.valid := io.kill
  dut.io.flush.bits.robIdx.value := io.killTag
  dut.io.flush.bits.robIdx.flag := io.killFlag
  dut.io.flush.bits.level := io.killSelf.asUInt
  val ctrl = dut.io.in.bits.ctrl
  ctrl.robIdx.value := io.tag; ctrl.robIdx.flag := io.flag
  ctrl.vecWen.get := true.B; ctrl.v0Wen.get := false.B
  ctrl.pdest := io.tag
  ctrl.vpu.get.vm := io.vm; ctrl.vpu.get.vill := io.vill
  ctrl.vpu.get.vsew := io.sew; ctrl.vpu.get.vlmul := io.lmul
  ctrl.vpu.get.vstart := io.start
  dut.io.in.bits.data.src(0) := io.a.asUInt
  dut.io.in.bits.data.src(1) := io.b.asUInt
  dut.io.in.bits.data.src(2) := io.old.asUInt
  dut.io.in.bits.data.src(3) := io.mask.asUInt
  dut.io.in.bits.data.src(4) := io.vl
  val ctrls = ctrl +: Seq.fill(2)(Reg(chiselTypeOf(ctrl)))
  val datas = dut.io.in.bits.data +: Seq.fill(2)(Reg(chiselTypeOf(dut.io.in.bits.data)))
  val valids = io.valid +: Seq.fill(2)(RegInit(false.B))
  for (i <- 1 to 2) {
    ctrls(i) := ctrls(i-1); datas(i) := datas(i-1)
    valids(i) := valids(i-1) && !ctrls(i-1).robIdx.needFlush(dut.io.flush)
  }
  for (i <- 0 to 2) {
    dut.io.in.bits.ctrlPipe.get(i) := ctrls(i)
    dut.io.in.bits.dataPipe.get(i) := datas(i)
    dut.io.in.bits.validPipe.get(i) := valids(i)
  }
  io.outValid := dut.io.out.valid
  io.result := dut.io.out.bits.res.data.asTypeOf(io.result)
  io.illegal := dut.io.out.bits.ctrl.exceptionVec.get(ExceptionNO.illegalInstr)
  io.outTag := dut.io.out.bits.ctrl.robIdx.value
  io.outFlag := dut.io.out.bits.ctrl.robIdx.flag
  io.wen := dut.io.out.bits.ctrl.vecWen.get
}

class VDotDecodeHarness(implicit p: Parameters) extends Module {
  val io = IO(new Bundle {
    val word = Input(UInt(32.W)); val sew = Input(UInt(3.W))
    val lmul = Input(UInt(3.W)); val vill = Input(Bool())
    val start = Input(UInt(8.W)); val vsOff = Input(Bool())
    val isVdot = Output(Bool()); val complex = Output(Bool())
    val illegal = Output(Bool()); val oldDep = Output(Bool())
    val uops = Output(UInt(8.W)); val writes = Output(UInt(8.W))
  })
  val d = Module(new DecodeUnit)
  d.io.enq := 0.U.asTypeOf(d.io.enq)
  d.io.csrCtrl := 0.U.asTypeOf(d.io.csrCtrl)
  d.io.fromCSR := 0.U.asTypeOf(d.io.fromCSR)
  d.io.enq.ctrlFlow.instr := io.word
  d.io.enq.vtype.vsew := io.sew; d.io.enq.vtype.vlmul := io.lmul
  d.io.enq.vtype.illegal := io.vill; d.io.enq.vstart := io.start
  d.io.fromCSR.illegalInst.vsIsOff := io.vsOff
  io.isVdot := FuType.FuTypeOrR(d.io.deq.decodedInst.fuType, Seq(FuType.vdot))
  io.complex := d.io.deq.isComplex
val v = Module(new VecExceptionGen)
  v.io.inst := io.word
  v.io.decodedInst := d.io.deq.decodedInst
  v.io.vtype := d.io.enq.vtype
  v.io.vstart := io.start
  io.illegal := d.io.deq.decodedInst.exceptionVec(ExceptionNO.illegalInstr) || v.io.illegalInst
  io.oldDep := d.io.deq.decodedInst.vpu.isDependOldVd
  io.uops := d.io.deq.uopInfo.numOfUop
  io.writes := d.io.deq.uopInfo.numOfWB
}

class VDotLocalTest extends AnyFlatSpec with ChiselScalatestTester {
  val c = new MinimalConfig
  implicit val p: Parameters = c.alterPartial { case XSCoreParamsKey => c(XSTileKey).head }
  def pack(xs: Seq[Int]): BigInt = xs.zipWithIndex.map { case(x,i) => BigInt(x & 255) << (8*i) }.sum
  behavior of "VDot v0.1 real XiangShan interfaces"
  // chiseltest 6 emits the former WData typedef; Verilator 5.052 calls it EData.
  def annotations(name: String) = Seq(VerilatorBackendAnnotation,
    VerilatorCFlags(Seq("-DWData=EData")),
    TargetDirAnnotation(sys.env("VDOT_TEST_DIR") + "/" + name))

  it should "recognize exact encoding and retain vector single-uop legality" in {
    val pattern = VdotInstructions.VDOT_VV
    var count = 0
    for (vm <- 0 to 1; vd <- 0 until 32; vs1 <- 0 until 32; vs2 <- 0 until 32) {
      val word = BigInt(0x0b) | BigInt(vm)<<25 | BigInt(vs2)<<20 | BigInt(vs1)<<15 | BigInt(vd)<<7
      assert((word & pattern.mask) == pattern.value); count += 1
    }
    assert(count == 65536)
    test(new VDotDecodeHarness).withAnnotations(annotations("decode")) { d =>
      d.io.sew.poke(0.U); d.io.lmul.poke(0.U); d.io.vill.poke(false.B)
      d.io.start.poke(0.U); d.io.vsOff.poke(false.B)
      for (word <- Seq(0x0220818bL, 0x0020800bL, 0x0000000bL, 0x03ff8f8bL)) {
        d.io.word.poke(word.U)
        d.io.isVdot.expect(true.B); d.io.complex.expect(true.B)
        d.io.uops.expect(1.U); d.io.writes.expect(1.U)
        d.io.oldDep.expect(true.B); d.io.illegal.expect(false.B)
      }
      for (enc <- 1 to 7) {
        // Real VType stores only two vsew bits: unsupported raw 4..7 are
        // represented by vill upstream. Raw 3-bit injection is a separate unit test.
        d.io.sew.poke((enc & 3).U); d.io.vill.poke((enc >= 4).B)
        d.io.illegal.expect(true.B); d.io.uops.expect(1.U)
        d.io.sew.poke(0.U); d.io.vill.poke(false.B)
        d.io.lmul.poke(enc.U); d.io.illegal.expect(true.B)
        d.io.lmul.poke(0.U)
      }
      d.io.vill.poke(true.B); d.io.illegal.expect(true.B); d.io.vill.poke(false.B)
      d.io.start.poke(1.U); d.io.illegal.expect(true.B); d.io.start.poke(0.U)
      d.io.vsOff.poke(true.B); d.io.illegal.expect(true.B); d.io.vsOff.poke(false.B)
      for (word <- Seq(0x0220918bL, 0x0620818bL, 0x022081afL, 0x021101d7L)) {
        d.io.word.poke(word.U); d.io.isVdot.expect(false.B)
      }
      d.io.word.poke(0x021101d7L.U); d.io.illegal.expect(false.B)
    }
    println("PASS VDOT_REAL_DECODE patterns=65536")
  }

  it should "align arithmetic, vl-zero, errors and full-ROB cancellation in two cycles" in {
    test(new VDotLocalHarness).withAnnotations(annotations("fu")) { d =>
def poke128(port: Vec[UInt], value: BigInt): Unit =
        port.zipWithIndex.foreach { case (part, i) => part.poke(((value >> (64*i)) & ((BigInt(1)<<64)-1)).U) }
      def expect128(port: Vec[UInt], value: BigInt): Unit =
        port.zipWithIndex.foreach { case (part, i) => part.expect(((value >> (64*i)) & ((BigInt(1)<<64)-1)).U) }
      d.io.valid.poke(false.B); poke128(d.io.a, 0); poke128(d.io.b, 0)
      poke128(d.io.old, 0); poke128(d.io.mask, 255); d.io.vl.poke(8.U)
      d.io.vm.poke(true.B); d.io.sew.poke(0.U); d.io.lmul.poke(0.U)
      d.io.start.poke(0.U); d.io.vill.poke(false.B); d.io.tag.poke(5.U)
      d.io.flag.poke(false.B); d.io.kill.poke(false.B); d.io.killTag.poke(4.U)
      d.io.killFlag.poke(false.B); d.io.killSelf.poke(false.B)
      d.clock.step(3)
      val old = BigInt("fedcba9876543210abcdef0012345678",16)
      def issue(a: Seq[Int], b: Seq[Int], mask: Int, vm: Boolean, vl: Int,
                expected: BigInt, bad: Boolean = false): Unit = {
        poke128(d.io.a, pack(a)); poke128(d.io.b, pack(b)); poke128(d.io.old, old)
        poke128(d.io.mask, mask); d.io.vm.poke(vm.B); d.io.vl.poke(vl.U)
        d.io.valid.poke(true.B); d.clock.step(); d.io.outValid.expect(false.B)
        d.io.valid.poke(false.B); d.clock.step(); d.io.outValid.expect(true.B)
        expect128(d.io.result, expected); d.io.illegal.expect(bad.B)
        d.io.outTag.expect(5.U); d.io.wen.expect(true.B)
        d.clock.step(); d.io.outValid.expect(false.B)
      }
      issue(Seq.fill(8)(-128),Seq.fill(8)(-128),255,true,8,131072)
      issue(Seq.fill(8)(-128),Seq.fill(8)(127),255,true,16,BigInt(-130048)&((BigInt(1)<<32)-1))
      issue(1 to 16,Seq.fill(16)(1),0,true,8,36)
      issue(1 to 16,Seq.fill(16)(1),0,false,8,0)
      issue(1 to 16,Seq.fill(16)(1),0x55,false,8,16)
      issue(1 to 16,Seq.fill(16)(1),255,true,0,old)
      for (vl <- Seq(1,7,17,255)) issue(1 to 16,Seq.fill(16)(1),255,true,vl,old,true)
      d.io.start.poke(1.U); issue(1 to 16,Seq.fill(16)(1),255,true,0,old,true); d.io.start.poke(0.U)
      for ((killTag,killSelf,cancel) <- Seq((4,false,true),(5,false,false),(5,true,true),(6,true,false))) {
        d.io.vl.poke(8.U); d.io.valid.poke(true.B); d.clock.step()
        d.io.valid.poke(false.B); d.clock.step()
        d.io.killTag.poke(killTag.U); d.io.killSelf.poke(killSelf.B); d.io.kill.poke(true.B)
        d.io.outValid.expect((!cancel).B)
        d.clock.step(); d.io.kill.poke(false.B); d.io.outValid.expect(false.B)
      }
      // Across ROB wrap: flag=1/value=0 is younger than flag=0/value=last.
      d.io.tag.poke(0.U); d.io.flag.poke(true.B); d.io.valid.poke(true.B); d.clock.step()
      d.io.valid.poke(false.B); d.io.killTag.poke((p(XSCoreParamsKey).RobSize-1).U)
      d.io.killFlag.poke(false.B); d.io.killSelf.poke(false.B); d.io.kill.poke(true.B)
      d.clock.step(); d.io.outValid.expect(false.B); d.io.kill.poke(false.B)
      d.clock.step(3); d.io.outValid.expect(false.B)
    }
    println("PASS VDOT_REAL_FU latency=2 arithmetic/vl0/errors/redirect")
  }
}
