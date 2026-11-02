package xiangshan.backend.rob

import chisel3._
import chisel3.util._
import org.chipsalliance.cde.config.Parameters
import xiangshan._
import xiangshan.backend.decode.VdotInstructions

/** Functional ROB-indexed storage, deliberately independent of DebugMem.
  * Only the 16 variable encoding bits are stored. The ROB generation bit
  * prevents a reused index from identifying a different dynamic instruction.
  * Every allocation, including non-VDot, replaces the slot's classification.
  * Squashed entries may remain in storage; only a live ROB-head exception can
  * request a result, and allocation overwrites a slot before it is reused.
  */
class VdotTrapInstTable(implicit p: Parameters) extends XSModule {
  val io = IO(new Bundle {
    val alloc = Input(Vec(RenameWidth, Valid(new Bundle {
      val robIdx = new RobPtr
      val instr = UInt(32.W)
    })))
    val head = Input(new RobPtr)
    val trap = Input(Bool())
    val illegal = Input(Bool())
    val interrupt = Input(Bool())
    val out = Output(Valid(UInt(32.W)))
  })
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
}

object VdotTrapInstSelect {
  def apply(trap: Bool, interrupt: Bool, illegal: Bool,
            vdot: ValidIO[UInt], legacy: ValidIO[UInt]): ValidIO[UInt] = {
    val out = Wire(Valid(UInt(32.W)))
    val useVdot = trap && !interrupt && illegal && vdot.valid
    out.valid := Mux(useVdot, true.B, legacy.valid)
    out.bits := Mux(useVdot, vdot.bits, legacy.bits)
    out
  }
}
