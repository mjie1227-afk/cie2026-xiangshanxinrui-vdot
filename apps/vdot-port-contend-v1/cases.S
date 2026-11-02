.section .text
.option push
.option norvc
.balign 4
.globl contend_0
.type contend_0,@function
contend_0:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vcsr,0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    addi t0,a0,64
    vle8.v v4,(t0)
    vsetivli zero,8,e8,m1,tu,mu
.globl contend_0_gate
contend_0_gate:
    vdivu.vv v0,v1,v2
.globl contend_0_dot
contend_0_dot:
    .word 0x0020818b
.globl contend_0_iota
contend_0_iota:
    viota.m v4,v0
.globl contend_0_after
contend_0_after:
    csrr t0,vl
    sd t0,0(a2)
    csrr t0,vtype
    sd t0,8(a2)
    csrr t0,vstart
    sd t0,16(a2)
    csrr t0,vcsr
    sd t0,24(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    addi t0,a1,64
    vse8.v v4,(t0)
    ret

.balign 4
.globl contend_1
.type contend_1,@function
contend_1:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vcsr,0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    addi t0,a0,64
    vle8.v v4,(t0)
    vsetivli zero,8,e8,m1,tu,mu
.globl contend_1_gate
contend_1_gate:
    vdivu.vv v0,v1,v2
.globl contend_1_iota
contend_1_iota:
    viota.m v4,v0
.globl contend_1_dot
contend_1_dot:
    .word 0x0020818b
.globl contend_1_after
contend_1_after:
    csrr t0,vl
    sd t0,0(a2)
    csrr t0,vtype
    sd t0,8(a2)
    csrr t0,vstart
    sd t0,16(a2)
    csrr t0,vcsr
    sd t0,24(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    addi t0,a1,64
    vse8.v v4,(t0)
    ret

.balign 4
.globl contend_2
.type contend_2,@function
contend_2:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vcsr,0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    addi t0,a0,64
    vle8.v v4,(t0)
    vsetivli zero,8,e8,m1,tu,mu
.globl contend_2_gate
contend_2_gate:
    vdivu.vv v0,v1,v2
    vdivu.vv v0,v0,v2
.globl contend_2_dot
contend_2_dot:
    .word 0x0020818b
.globl contend_2_iota
contend_2_iota:
    viota.m v4,v0
.globl contend_2_after
contend_2_after:
    csrr t0,vl
    sd t0,0(a2)
    csrr t0,vtype
    sd t0,8(a2)
    csrr t0,vstart
    sd t0,16(a2)
    csrr t0,vcsr
    sd t0,24(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    addi t0,a1,64
    vse8.v v4,(t0)
    ret

.balign 4
.globl contend_3
.type contend_3,@function
contend_3:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrwi vcsr,0
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    addi t0,a0,64
    vle8.v v4,(t0)
    vsetivli zero,8,e8,m1,tu,mu
.globl contend_3_gate
contend_3_gate:
    vdivu.vv v0,v1,v2
    vdivu.vv v0,v0,v2
.globl contend_3_iota
contend_3_iota:
    viota.m v4,v0
.globl contend_3_dot
contend_3_dot:
    .word 0x0020818b
.globl contend_3_after
contend_3_after:
    csrr t0,vl
    sd t0,0(a2)
    csrr t0,vtype
    sd t0,8(a2)
    csrr t0,vstart
    sd t0,16(a2)
    csrr t0,vcsr
    sd t0,24(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    addi t0,a1,64
    vse8.v v4,(t0)
    ret

.option pop
