#include <stdint.h>
#include <klib.h>
static uint64_t before[4][2] __attribute__((aligned(16)));
static uint64_t after[4][2] __attribute__((aligned(16)));
static void init(void) {
  for (unsigned r=0;r<4;r++) for(unsigned w=0;w<2;w++) {
    uint64_t x=0;
    for(unsigned b=0;b<8;b++) x|=(uint64_t)((17+r*47+(w*8+b)*29)&255)<<(8*b);
    before[r][w]=x; after[r][w]=0xeeeeeeeeeeeeeeeeULL;
  }
  before[0][0]=(before[0][0]&~255ULL)|0xa5;
}
static uint32_t dot(unsigned s1,unsigned s2,unsigned vm) {
  int32_t sum=0;
  for(unsigned b=0;b<8;b++) if(vm || ((before[0][0]>>b)&1))
    sum+=(int32_t)(int8_t)(before[s1][0]>>(8*b))*(int32_t)(int8_t)(before[s2][0]>>(8*b));
  return (uint32_t)sum;
}
static int vectors(unsigned vd,unsigned s1,unsigned s2,unsigned vm,unsigned write) {
  for(unsigned r=0;r<4;r++) for(unsigned w=0;w<2;w++) {
    uint64_t want=(write && r==vd) ? (w==0 ? dot(s1,s2,vm):0) : before[r][w];
    if(after[r][w]!=want) { printf("FAIL vector r=%d word=%d\n",r,w); return 0; }
  }
  return 1;
}
extern uint64_t overlap_0(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_1(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_2(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_3(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_4(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_5(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_6(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_7(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_8(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_9(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_10(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_11(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_12(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_13(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
extern uint64_t overlap_14(const uint64_t [4][2], uint64_t [4][2], uint64_t, uint64_t);
static const struct {uint64_t (*f)(const uint64_t [4][2],uint64_t [4][2],uint64_t,uint64_t); unsigned d,s1,s2;} cases[]={
{overlap_0,1,2,3},
{overlap_1,0,1,2},
{overlap_2,1,0,2},
{overlap_3,1,2,0},
{overlap_4,1,1,2},
{overlap_5,1,2,1},
{overlap_6,2,1,1},
{overlap_7,0,0,1},
{overlap_8,0,1,0},
{overlap_9,1,0,0},
{overlap_10,0,1,1},
{overlap_11,1,0,1},
{overlap_12,1,1,0},
{overlap_13,1,1,1},
{overlap_14,0,0,0}};
int main(void) {
  unsigned count=0;
  for(unsigned p=0;p<15;p++) for(unsigned vm=0;vm<2;vm++) for(unsigned v=0;v<2;v++) {
    unsigned vl=v*8; init();
    uint64_t status=cases[p].f(before,after,vl,vm), csr, start;
    __asm__ volatile("csrr %0,vcsr" : "=r"(csr));
    __asm__ volatile("csrr %0,vstart" : "=r"(start));
    if(status!=(vl|0x300) || csr!=7 || start!=0 || !vectors(cases[p].d,cases[p].s1,cases[p].s2,vm,vl!=0)) {
      printf("FAIL overlap partition=%d vm=%d vl=%d status=%x\n",p,vm,vl,(unsigned)status); return 1;
    }
    count++;
  }
  printf("PASS VDOT_OVERLAP cases=%d partitions=15\n",count); return 0;
}
