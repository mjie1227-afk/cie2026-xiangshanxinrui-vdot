package xiangshan.backend.rob

import chisel3._
import chisel3.util._
import chiseltest._
import chiseltest.simulator.VerilatorCFlags
import firrtl2.options.TargetDirAnnotation
import org.chipsalliance.cde.config.Parameters
import org.scalatest.flatspec.AnyFlatSpec
import top.MinimalConfig
import xiangshan._
import xiangshan.backend.fu.NewCSR.CSRBundles.PrivState
import xiangshan.backend.fu.NewCSR.CSREvents.TrapEntryMEventModule

class VdotTrapHarness(implicit p: Parameters) extends XSModule {
  val table = Module(new VdotTrapInstTable)
  val io = IO(new Bundle {
    val alloc = Input(chiselTypeOf(table.io.alloc))
    val head = Input(new RobPtr)
    val trap = Input(Bool()); val illegal = Input(Bool()); val interrupt = Input(Bool())
    val legacy = Input(Valid(UInt(32.W)))
    val out = Output(Valid(UInt(32.W)))
    val mtval = Output(UInt(64.W)); val mtvalValid = Output(Bool())
  })
  table.io.alloc := io.alloc; table.io.head := io.head
  table.io.trap := io.trap; table.io.illegal := io.illegal; table.io.interrupt := io.interrupt
  val trap = RegNext(io.trap, false.B)
  val illegal = RegEnable(io.illegal, io.trap)
  val interrupt = RegEnable(io.interrupt, io.trap)
  io.out := VdotTrapInstSelect(trap, interrupt, illegal, table.io.out, io.legacy)
  // Exercise the production mtval event, not a replica of its mux.
  val event = Module(new TrapEntryMEventModule)
  event.valid := trap
  // Unused privilege-update fields include enums with no zero encoding.
  // Constrain every input contributing to the mtval path exercised here.
  event.in := DontCare
  event.in.isFetchMalAddr := false.B
  event.in.isCrossPageIPF := false.B
  event.in.isHls := false.B
  event.in.isFetchBkpt := false.B
  event.in.hasDTExcp := false.B
  event.in.trapPc := 0.U
  event.in.fetchMalTval := 0.U
  event.in.iMode := PrivState.ModeM
  event.in.dMode := PrivState.ModeM
  event.in.privState := PrivState.ModeM
  event.in.causeNO.ExceptionCode := Mux(illegal, ExceptionNO.EX_II.U, ExceptionNO.EX_BP.U)
  event.in.causeNO.Interrupt := interrupt
  event.in.trapInst := io.out
  io.mtval := event.out.mtval.bits.ALL.asUInt
  io.mtvalValid := event.out.mtval.valid
}

class VdotTrapInstTest extends AnyFlatSpec with ChiselScalatestTester {
  val c = new MinimalConfig
  implicit val p: Parameters = c.alterPartial { case XSCoreParamsKey => c(XSTileKey).head }
  behavior of "precise VDot instruction to mtval"
  it should "preserve encoding and ROB lifetime while leaving legacy traps alone" in {
    test(new VdotTrapHarness).withAnnotations(Seq(VerilatorBackendAnnotation,
      VerilatorCFlags(Seq("-DWData=EData")), TargetDirAnnotation(sys.env("VDOT_TEST_DIR")+"/mtval"))) { d =>
      for(a <- d.io.alloc) { a.valid.poke(false.B); a.bits.robIdx.flag.poke(false.B); a.bits.robIdx.value.poke(0.U); a.bits.instr.poke(0.U) }
      d.io.head.flag.poke(false.B); d.io.head.value.poke(0.U)
      d.io.trap.poke(false.B); d.io.illegal.poke(true.B); d.io.interrupt.poke(false.B)
      d.io.legacy.valid.poke(false.B); d.io.legacy.bits.poke(0.U)
      d.clock.step(); d.io.out.valid.expect(false.B)
      var checks=0
      def alloc(slot:Int, flag:Boolean, word:Long, lane:Int=0):Unit = {
        d.io.alloc(lane).valid.poke(true.B); d.io.alloc(lane).bits.robIdx.value.poke(slot.U)
        d.io.alloc(lane).bits.robIdx.flag.poke(flag.B); d.io.alloc(lane).bits.instr.poke(word.U)
      }
      def tickAlloc():Unit = { d.clock.step(); d.io.alloc.foreach(_.valid.poke(false.B)) }
      def trap(slot:Int,flag:Boolean,word:Long,expected:Boolean=true):Unit = {
        d.io.head.value.poke(slot.U); d.io.head.flag.poke(flag.B); d.io.trap.poke(true.B)
        d.clock.step(); d.io.trap.poke(false.B)
        d.io.out.valid.expect(expected.B); d.io.mtvalValid.expect(true.B)
        if(expected) { d.io.out.bits.expect(word.U); d.io.mtval.expect(word.U) }
        else d.io.mtval.expect(0.U)
        d.clock.step(); d.io.out.valid.expect(d.io.legacy.valid.peek()); checks+=1
      }
      // Regression for the observed first illegal instruction, followed by a
      // different younger VDot: selection must use the precise ROB head.
      alloc(4,false,0x0020818bL); alloc(5,false,0x03ff8f8bL,1); tickAlloc()
      trap(4,false,0x0020818bL); trap(5,false,0x03ff8f8bL)
      // Generation mismatch, canceled instruction with no trap, and index reuse.
      trap(4,true,0,expected=false)
      d.io.head.value.poke(5.U); d.clock.step(3); d.io.out.valid.expect(false.B)
      alloc(4,true,0x00000013L); tickAlloc(); trap(4,true,0,expected=false)
      alloc(4,true,0x0220818bL); tickAlloc(); trap(4,true,0x0220818bL)
      // Same-generation reuse after a redirect also overwrites classification.
      alloc(4,true,0x021101d7L); tickAlloc(); trap(4,true,0,expected=false)
      // No illegal exception and interrupts must never select a stored VDot.
      alloc(6,false,0x0020818bL); tickAlloc()
      d.io.illegal.poke(false.B); trap(6,false,0,expected=false); d.io.illegal.poke(true.B)
      d.io.interrupt.poke(true.B); trap(6,false,0,expected=false); d.io.interrupt.poke(false.B)
      // Legacy CSR/decode information is preserved, including compressed bits.
      for(word <- Seq(0x7ff01073L,0x00000000L,0x00009002L)) {
        d.io.legacy.valid.poke(true.B); d.io.legacy.bits.poke(word.U)
        trap(4,true,word)
      }
      // A precise VDot trap outranks an unrelated younger legacy candidate.
      d.io.legacy.valid.poke(true.B); d.io.legacy.bits.poke(0xffffffffL.U)
      trap(6,false,0x0020818bL)
      d.io.legacy.valid.poke(false.B)
      // Check all 16-bit variable-field combinations in actual RTL storage and
      // the actual CSR event. Unused opcode/funct fields are reconstructed.
      for(fields <- 0 until 65536) {
        val word=0xbL | ((fields&31).toLong<<7) | (((fields>>5)&31).toLong<<15) |
          (((fields>>10)&31).toLong<<20) | (((fields>>15)&1).toLong<<25)
        alloc(7,false,word); tickAlloc(); trap(7,false,word)
      }
      // Reset invalidates all old classifications, including an allocated slot.
      d.reset.poke(true.B); d.clock.step(); d.reset.poke(false.B)
      trap(7,false,0,expected=false)
      println(s"PASS VDOT_MTVAL_PATH checks=$checks variable_encodings=65536 real_TrapEntryMEvent=true")
    }
  }
}
