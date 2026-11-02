    .section .text
    .balign 4
    .globl vdot_case
    .type vdot_case, @function
vdot_case:
    # a0=A, a1=B, a2=oldVd, a3=out, a4=mask bytes, a5=VL, a6=vm
    li t0, 0x200
    csrs mstatus, t0
    csrwi vstart, 0
    csrwi vxrm, 3
    csrwi vxsat, 1
    vsetivli zero, 16, e8, m1, tu, mu
    vle8.v v1, (a0)
    vle8.v v2, (a1)
    vle8.v v3, (a2)
    vlm.v v0, (a4)
    vsetvli zero, a5, e8, m1, tu, mu
    # Make vdot itself responsible for VS Dirty, including legal VL=0.
    li t0, 0x600
    csrc mstatus, t0
    li t0, 0x200
    csrs mstatus, t0
    beqz a6, .Lmasked
    .globl vdot_unmasked_target
vdot_unmasked_target:
    .word 0x0220818b  # vdot.vv v3,v2,v1, vm=1
    j .Lcapture
.Lmasked:
    .globl vdot_masked_target
vdot_masked_target:
    .word 0x0020818b  # vdot.vv v3,v2,v1, vm=0
.Lcapture:
    csrr t0, mstatus
    srli t0, t0, 9
    andi t0, t0, 3
    slli t0, t0, 8
    csrr a0, vl
    or a0, a0, t0     # return VL | (VS << 8), captured before later vector ops
    vsetivli zero, 16, e8, m1, tu, mu
    vse8.v v3, (a3)
    ret
    .size vdot_case, .-vdot_case
