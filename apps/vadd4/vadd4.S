    .section .text
    .balign 4
    .globl vadd4
    .type vadd4, @function
vadd4:
    # This AM program runs in M-mode. Its startup enables FP, but not vectors.
    li t0, 0x200
    csrs mstatus, t0              # VS != Off: permit vector instructions.
    csrwi vstart, 0               # Start at element 0.

    # a3 contains AVL=4; t1 receives the actual VL chosen by the hardware.
    vsetvli t1, a3, e32, m1, ta, ma
    bne t1, a3, .Ldone            # Do not claim a full result if VL is too small.
    vle32.v v1, (a0)              # A[0:VL] -> v1
    vle32.v v2, (a1)              # B[0:VL] -> v2
    .globl vadd4_target
vadd4_target:
    vadd.vv v3, v1, v2            # v3[i] = v1[i] + v2[i]
    vse32.v v3, (a2)              # v3 -> C[0:VL]
.Ldone:
    mv a0, t1                    # Return actual VL to C.
    ret
    .size vadd4, .-vadd4
