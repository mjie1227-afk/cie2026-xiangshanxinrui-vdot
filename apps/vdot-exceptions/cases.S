.section .text
.balign 4
.globl exception_case
.type exception_case,@function
exception_case:
    addi sp,sp,-64
    sd ra,0(sp)
    sd s0,8(sp)
    sd s1,16(sp)
    sd s2,24(sp)
    sd s3,32(sp)
    sd s4,40(sp)
    sd s5,48(sp)
    mv s0,a3
    mv s1,a1
    mv s2,a2
    mv s3,a0
    csrr s4,mtvec
    csrr s5,mscratch
    la t0,matrix_trap
    csrw mtvec,t0
    csrw mscratch,s0
    # Enable ordinary exceptions under this build's Smrnmi/Smdbltrp setup.
    .word 0x74446073
    li t0,0x40000000000
    csrc mstatus,t0
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, s3, 0
    vle8.v v0, (t0)
    addi t0, s3, 16
    vle8.v v1, (t0)
    addi t0, s3, 32
    vle8.v v2, (t0)
    addi t0, s3, 48
    vle8.v v3, (t0)
    ld t0,0(s2)
    ld t1,8(s2)
    vsetvl zero,t0,t1
    ld t0,16(s2)
    csrw vstart,t0
    csrr t0,vl
    sd t0,48(s0)
    csrr t0,vtype
    sd t0,56(s0)
    csrr t0,vstart
    sd t0,64(s0)
    csrr t0,vcsr
    sd t0,72(s0)
    li t0,0x600
    csrc mstatus,t0
    ld t0,24(s2)
    slli t0,t0,9
    csrs mstatus,t0
    ld t0,32(s2)
    li t1,1
    beq t0,t1,.Lbad3
    li t1,2
    beq t0,t1,.Lbad6
    ld t0,40(s2)
    beqz t0,.Lmasked
    la t0,target_vm1
    sd t0,40(s0)
target_vm1:
    .word 0x0220818b
    j .Lcapture
.Lmasked:
    la t0,target_vm0
    sd t0,40(s0)
target_vm0:
    .word 0x0020818b
    j .Lcapture
.Lbad3:
    la t0,target_bad3
    sd t0,40(s0)
target_bad3:
    .word 0x0220918b
    j .Lcapture
.Lbad6:
    la t0,target_bad6
    sd t0,40(s0)
target_bad6:
    .word 0x0620818b
.Lcapture:
    csrr t0,mstatus
    sd t0,112(s0)
    li t0,0x200
    csrs mstatus,t0
    csrr t0,vl
    sd t0,80(s0)
    csrr t0,vtype
    sd t0,88(s0)
    csrr t0,vstart
    sd t0,96(s0)
    csrr t0,vcsr
    sd t0,104(s0)
    csrwi vstart,0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, s1, 0
    vse8.v v0, (t0)
    addi t0, s1, 16
    vse8.v v1, (t0)
    addi t0, s1, 32
    vse8.v v2, (t0)
    addi t0, s1, 48
    vse8.v v3, (t0)
    csrw mtvec,s4
    csrw mscratch,s5
    ld a0,0(s0)
    ld ra,0(sp)
    ld s0,8(sp)
    ld s1,16(sp)
    ld s2,24(sp)
    ld s3,32(sp)
    ld s4,40(sp)
    ld s5,48(sp)
    addi sp,sp,64
    ret
.size exception_case,.-exception_case
.balign 4
matrix_trap:
    csrrw t0,mscratch,t0
    sd t1,120(t0)
    ld t1,0(t0)
    addi t1,t1,1
    sd t1,0(t0)
    csrr t1,mcause
    sd t1,8(t0)
    csrr t1,mepc
    sd t1,16(t0)
    csrr t1,mtval
    sd t1,24(t0)
    csrr t1,mstatus
    sd t1,32(t0)
    ld t1,0(t0)
    addi t1,t1,-1
    bnez t1,.Lunexpected
    ld t1,8(t0)
    addi t1,t1,-2
    bnez t1,.Lunexpected
    ld t1,16(t0)
    ld t0,40(t0)
    bne t0,t1,.Lunexpected
    addi t1,t1,4
    csrw mepc,t1
    # s0 is the wrapper's result pointer and is preserved across this handler.
    mv t0,s0
    ld t1,120(t0)
    csrrw t0,mscratch,t0
    mret
.Lunexpected:
    li a0,1
    .word 0x0000006b
    j .Lunexpected
