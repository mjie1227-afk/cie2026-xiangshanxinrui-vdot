.section .text
.option push
.option norvc
.balign 4
.globl native_vm0
.type native_vm0,@function
native_vm0:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrw vcsr,a5
    csrw fflags,a6
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    vsetvl zero,a3,a4
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
.globl native_vm0_kernel_begin
native_vm0_kernel_begin:
    .word 0x0020818b
.globl native_vm0_kernel_end
native_vm0_kernel_end:
    csrr t0,mstatus
    sd t0,0(a2)
    csrr t0,vl
    sd t0,8(a2)
    csrr t0,vtype
    sd t0,16(a2)
    csrr t0,vstart
    sd t0,24(a2)
    csrr t0,vcsr
    sd t0,32(a2)
    csrr t0,fflags
    sd t0,40(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    ret

.balign 4
.globl native_vm1
.type native_vm1,@function
native_vm1:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrw vcsr,a5
    csrw fflags,a6
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    vsetvl zero,a3,a4
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
.globl native_vm1_kernel_begin
native_vm1_kernel_begin:
    .word 0x0220818b
.globl native_vm1_kernel_end
native_vm1_kernel_end:
    csrr t0,mstatus
    sd t0,0(a2)
    csrr t0,vl
    sd t0,8(a2)
    csrr t0,vtype
    sd t0,16(a2)
    csrr t0,vstart
    sd t0,24(a2)
    csrr t0,vcsr
    sd t0,32(a2)
    csrr t0,fflags
    sd t0,40(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    ret

.balign 4
.globl rvv_m1_vm0
.type rvv_m1_vm0,@function
rvv_m1_vm0:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrw vcsr,a5
    csrw fflags,a6
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    vsetvl zero,a3,a4
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
.globl rvv_m1_vm0_kernel_begin
rvv_m1_vm0_kernel_begin:
    beqz a3,rvv_m1_vm0_restore
    vsetivli zero,8,e8,m1,tu,mu
    vwmul.vv v8,v1,v2
    vsetivli zero,4,e32,m1,tu,mu
    vmv.v.i v3,0
    vmv.v.i v16,0
    vsetivli zero,8,e16,m2,tu,mu
    vwredsum.vs v3,v8,v16,v0.t
rvv_m1_vm0_restore:
    vsetvl zero,a3,a4
.globl rvv_m1_vm0_kernel_end
rvv_m1_vm0_kernel_end:
    csrr t0,mstatus
    sd t0,0(a2)
    csrr t0,vl
    sd t0,8(a2)
    csrr t0,vtype
    sd t0,16(a2)
    csrr t0,vstart
    sd t0,24(a2)
    csrr t0,vcsr
    sd t0,32(a2)
    csrr t0,fflags
    sd t0,40(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    ret

.balign 4
.globl rvv_m1_vm1
.type rvv_m1_vm1,@function
rvv_m1_vm1:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrw vcsr,a5
    csrw fflags,a6
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    vsetvl zero,a3,a4
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
.globl rvv_m1_vm1_kernel_begin
rvv_m1_vm1_kernel_begin:
    beqz a3,rvv_m1_vm1_restore
    vsetivli zero,8,e8,m1,tu,mu
    vwmul.vv v8,v1,v2
    vsetivli zero,4,e32,m1,tu,mu
    vmv.v.i v3,0
    vmv.v.i v16,0
    vsetivli zero,8,e16,m2,tu,mu
    vwredsum.vs v3,v8,v16
rvv_m1_vm1_restore:
    vsetvl zero,a3,a4
.globl rvv_m1_vm1_kernel_end
rvv_m1_vm1_kernel_end:
    csrr t0,mstatus
    sd t0,0(a2)
    csrr t0,vl
    sd t0,8(a2)
    csrr t0,vtype
    sd t0,16(a2)
    csrr t0,vstart
    sd t0,24(a2)
    csrr t0,vcsr
    sd t0,32(a2)
    csrr t0,fflags
    sd t0,40(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    ret

.balign 4
.globl rvv_mf2_vm0
.type rvv_mf2_vm0,@function
rvv_mf2_vm0:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrw vcsr,a5
    csrw fflags,a6
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    vsetvl zero,a3,a4
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
.globl rvv_mf2_vm0_kernel_begin
rvv_mf2_vm0_kernel_begin:
    beqz a3,rvv_mf2_vm0_restore
    vsetivli zero,8,e8,mf2,tu,mu
    vwmul.vv v8,v1,v2
    vsetivli zero,4,e32,m1,tu,mu
    vmv.v.i v3,0
    vmv.v.i v16,0
    vsetivli zero,8,e16,m1,tu,mu
    vwredsum.vs v3,v8,v16,v0.t
rvv_mf2_vm0_restore:
    vsetvl zero,a3,a4
.globl rvv_mf2_vm0_kernel_end
rvv_mf2_vm0_kernel_end:
    csrr t0,mstatus
    sd t0,0(a2)
    csrr t0,vl
    sd t0,8(a2)
    csrr t0,vtype
    sd t0,16(a2)
    csrr t0,vstart
    sd t0,24(a2)
    csrr t0,vcsr
    sd t0,32(a2)
    csrr t0,fflags
    sd t0,40(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    ret

.balign 4
.globl rvv_mf2_vm1
.type rvv_mf2_vm1,@function
rvv_mf2_vm1:
    li t0,0x2200
    csrs mstatus,t0
    csrwi vstart,0
    csrw vcsr,a5
    csrw fflags,a6
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a0,0
    vle8.v v0,(t0)
    addi t0,a0,16
    vle8.v v1,(t0)
    addi t0,a0,32
    vle8.v v2,(t0)
    addi t0,a0,48
    vle8.v v3,(t0)
    vsetvl zero,a3,a4
    li t0,0x600
    csrc mstatus,t0
    li t0,0x400
    csrs mstatus,t0
.globl rvv_mf2_vm1_kernel_begin
rvv_mf2_vm1_kernel_begin:
    beqz a3,rvv_mf2_vm1_restore
    vsetivli zero,8,e8,mf2,tu,mu
    vwmul.vv v8,v1,v2
    vsetivli zero,4,e32,m1,tu,mu
    vmv.v.i v3,0
    vmv.v.i v16,0
    vsetivli zero,8,e16,m1,tu,mu
    vwredsum.vs v3,v8,v16
rvv_mf2_vm1_restore:
    vsetvl zero,a3,a4
.globl rvv_mf2_vm1_kernel_end
rvv_mf2_vm1_kernel_end:
    csrr t0,mstatus
    sd t0,0(a2)
    csrr t0,vl
    sd t0,8(a2)
    csrr t0,vtype
    sd t0,16(a2)
    csrr t0,vstart
    sd t0,24(a2)
    csrr t0,vcsr
    sd t0,32(a2)
    csrr t0,fflags
    sd t0,40(a2)
    vsetivli zero,16,e8,m1,tu,mu
    addi t0,a1,0
    vse8.v v0,(t0)
    addi t0,a1,16
    vse8.v v1,(t0)
    addi t0,a1,32
    vse8.v v2,(t0)
    addi t0,a1,48
    vse8.v v3,(t0)
    ret

.option pop
