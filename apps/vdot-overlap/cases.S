.section .text
.balign 4
.globl overlap_0
.type overlap_0, @function
overlap_0:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask0
    .word 0x0231008b
    j .Ldone0
.Lmask0:
    .word 0x0031008b
.Ldone0:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_0,.-overlap_0

.balign 4
.globl overlap_1
.type overlap_1, @function
overlap_1:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask1
    .word 0x0220800b
    j .Ldone1
.Lmask1:
    .word 0x0020800b
.Ldone1:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_1,.-overlap_1

.balign 4
.globl overlap_2
.type overlap_2, @function
overlap_2:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask2
    .word 0x0220008b
    j .Ldone2
.Lmask2:
    .word 0x0020008b
.Ldone2:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_2,.-overlap_2

.balign 4
.globl overlap_3
.type overlap_3, @function
overlap_3:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask3
    .word 0x0201008b
    j .Ldone3
.Lmask3:
    .word 0x0001008b
.Ldone3:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_3,.-overlap_3

.balign 4
.globl overlap_4
.type overlap_4, @function
overlap_4:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask4
    .word 0x0220808b
    j .Ldone4
.Lmask4:
    .word 0x0020808b
.Ldone4:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_4,.-overlap_4

.balign 4
.globl overlap_5
.type overlap_5, @function
overlap_5:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask5
    .word 0x0211008b
    j .Ldone5
.Lmask5:
    .word 0x0011008b
.Ldone5:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_5,.-overlap_5

.balign 4
.globl overlap_6
.type overlap_6, @function
overlap_6:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask6
    .word 0x0210810b
    j .Ldone6
.Lmask6:
    .word 0x0010810b
.Ldone6:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_6,.-overlap_6

.balign 4
.globl overlap_7
.type overlap_7, @function
overlap_7:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask7
    .word 0x0210000b
    j .Ldone7
.Lmask7:
    .word 0x0010000b
.Ldone7:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_7,.-overlap_7

.balign 4
.globl overlap_8
.type overlap_8, @function
overlap_8:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask8
    .word 0x0200800b
    j .Ldone8
.Lmask8:
    .word 0x0000800b
.Ldone8:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_8,.-overlap_8

.balign 4
.globl overlap_9
.type overlap_9, @function
overlap_9:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask9
    .word 0x0200008b
    j .Ldone9
.Lmask9:
    .word 0x0000008b
.Ldone9:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_9,.-overlap_9

.balign 4
.globl overlap_10
.type overlap_10, @function
overlap_10:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask10
    .word 0x0210800b
    j .Ldone10
.Lmask10:
    .word 0x0010800b
.Ldone10:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_10,.-overlap_10

.balign 4
.globl overlap_11
.type overlap_11, @function
overlap_11:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask11
    .word 0x0210008b
    j .Ldone11
.Lmask11:
    .word 0x0010008b
.Ldone11:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_11,.-overlap_11

.balign 4
.globl overlap_12
.type overlap_12, @function
overlap_12:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask12
    .word 0x0200808b
    j .Ldone12
.Lmask12:
    .word 0x0000808b
.Ldone12:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_12,.-overlap_12

.balign 4
.globl overlap_13
.type overlap_13, @function
overlap_13:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask13
    .word 0x0210808b
    j .Ldone13
.Lmask13:
    .word 0x0010808b
.Ldone13:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_13,.-overlap_13

.balign 4
.globl overlap_14
.type overlap_14, @function
overlap_14:
    li t0,0x200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vxrm,3
    csrwi vxsat,1
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a0, 0
    vle8.v v0, (t0)
    addi t0, a0, 16
    vle8.v v1, (t0)
    addi t0, a0, 32
    vle8.v v2, (t0)
    addi t0, a0, 48
    vle8.v v3, (t0)
    vsetvli zero,a2,e8,m1,tu,mu
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
    beqz a3,.Lmask14
    .word 0x0200000b
    j .Ldone14
.Lmask14:
    .word 0x0000000b
.Ldone14:
    csrr t0,mstatus
    srli t0,t0,9
    andi t0,t0,3
    slli t0,t0,8
    csrr a0,vl
    or a0,a0,t0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0, a1, 0
    vse8.v v0, (t0)
    addi t0, a1, 16
    vse8.v v1, (t0)
    addi t0, a1, 32
    vse8.v v2, (t0)
    addi t0, a1, 48
    vse8.v v3, (t0)
    ret
.size overlap_14,.-overlap_14
