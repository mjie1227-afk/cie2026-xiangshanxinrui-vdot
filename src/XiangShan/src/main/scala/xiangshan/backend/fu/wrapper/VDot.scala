package xiangshan.backend.fu.wrapper

import chisel3._
import chisel3.util._
import org.chipsalliance.cde.config.Parameters
import xiangshan.ExceptionNO.illegalInstr
import xiangshan.backend.fu.FuConfig
import xiangshan.backend.fu.vector.VecPipedFuncUnit

/** v0.1 fixed-eight signed INT8 reduction. No generic destination MGU. */
class VDot(cfg: FuConfig)(implicit p: Parameters) extends VecPipedFuncUnit(cfg) {
  require(VLEN == 128 && cfg.destDataBits == 128)
  require(latency == 2 && latdiff == 0)

  val products = VecInit((0 until 8).map { i =>
    val product = vs1(8*i+7, 8*i).asSInt * vs2(8*i+7, 8*i).asSInt
    Mux(srcMask(i), product, 0.S(16.W))
  })
  val p1 = S1Reg(products)
  val pairs = (0 until 4).map(i => p1(2*i) +& p1(2*i+1))
  val halves = (0 until 2).map(i => pairs(2*i) +& pairs(2*i+1))
  val sum = halves(0) +& halves(1) // 19 bits, including +131072
  val result = S2Reg(Cat(0.U(96.W), sum.pad(32).asUInt))

  // The compact type/VS legality is checked upstream; retain a local guard.
  val illegal = outVecCtrl.vill || outVecCtrl.vsew =/= 0.U ||
    outVecCtrl.vlmul =/= 0.U || outVstart =/= 0.U ||
    (outVl =/= 0.U && (outVl < 8.U || outVl > 16.U))
  io.out.bits.res.data := Mux(outVl === 0.U || illegal, outOldVd, result)
  io.out.bits.ctrl.exceptionVec.get(illegalInstr) := illegal
  // Keep vecWen/v0Wen for legal vl=0: the new physical destination needs oldVd.
  // CSR updates and precise exceptions remain on the ordinary commit path.
  io.out.valid := fixValidVec.last && !outCtrl.robIdx.needFlush(io.flush)
}
