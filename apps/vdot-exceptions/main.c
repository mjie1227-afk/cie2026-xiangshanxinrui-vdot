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

typedef struct {uint64_t avl,type,start,vs,kind,vm;} Config;
typedef struct {uint64_t traps,cause,epc,tval,trap_status,expected_pc,bvl,btype,bstart,bcsr,avl,atype,astart,acsr,status,saved_t1;} Result;
extern uint64_t exception_case(const uint64_t [4][2],uint64_t [4][2],const Config*,Result*);
static const struct {const char *name; Config cfg; uint64_t vl,type; unsigned legal;} cases[]={
{"legal-before",{8ULL,0ULL,0ULL,2ULL,0ULL,1ULL},8ULL,0ULL,1},
{"short-1-vm0",{1ULL,0ULL,0ULL,2ULL,0ULL,0ULL},1ULL,0ULL,0},
{"short-1-vm1",{1ULL,0ULL,0ULL,2ULL,0ULL,1ULL},1ULL,0ULL,0},
{"short-2-vm0",{2ULL,0ULL,0ULL,2ULL,0ULL,0ULL},2ULL,0ULL,0},
{"short-2-vm1",{2ULL,0ULL,0ULL,2ULL,0ULL,1ULL},2ULL,0ULL,0},
{"short-3-vm0",{3ULL,0ULL,0ULL,2ULL,0ULL,0ULL},3ULL,0ULL,0},
{"short-3-vm1",{3ULL,0ULL,0ULL,2ULL,0ULL,1ULL},3ULL,0ULL,0},
{"short-4-vm0",{4ULL,0ULL,0ULL,2ULL,0ULL,0ULL},4ULL,0ULL,0},
{"short-4-vm1",{4ULL,0ULL,0ULL,2ULL,0ULL,1ULL},4ULL,0ULL,0},
{"short-5-vm0",{5ULL,0ULL,0ULL,2ULL,0ULL,0ULL},5ULL,0ULL,0},
{"short-5-vm1",{5ULL,0ULL,0ULL,2ULL,0ULL,1ULL},5ULL,0ULL,0},
{"short-6-vm0",{6ULL,0ULL,0ULL,2ULL,0ULL,0ULL},6ULL,0ULL,0},
{"short-6-vm1",{6ULL,0ULL,0ULL,2ULL,0ULL,1ULL},6ULL,0ULL,0},
{"short-7-vm0",{7ULL,0ULL,0ULL,2ULL,0ULL,0ULL},7ULL,0ULL,0},
{"short-7-vm1",{7ULL,0ULL,0ULL,2ULL,0ULL,1ULL},7ULL,0ULL,0},
{"sew-1-vl0",{0ULL,8ULL,0ULL,2ULL,0ULL,1ULL},0ULL,8ULL,0},
{"sew-1-vl8",{8ULL,8ULL,0ULL,2ULL,0ULL,1ULL},8ULL,8ULL,0},
{"sew-2-vl0",{0ULL,16ULL,0ULL,2ULL,0ULL,1ULL},0ULL,16ULL,0},
{"sew-2-vl8",{8ULL,16ULL,0ULL,2ULL,0ULL,1ULL},4ULL,16ULL,0},
{"sew-3-vl0",{0ULL,24ULL,0ULL,2ULL,0ULL,1ULL},0ULL,24ULL,0},
{"sew-3-vl8",{8ULL,24ULL,0ULL,2ULL,0ULL,1ULL},2ULL,24ULL,0},
{"sew-4-vl0",{0ULL,32ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"sew-4-vl8",{8ULL,32ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"sew-5-vl0",{0ULL,40ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"sew-5-vl8",{8ULL,40ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"sew-6-vl0",{0ULL,48ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"sew-6-vl8",{8ULL,48ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"sew-7-vl0",{0ULL,56ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"sew-7-vl8",{8ULL,56ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"lmul-1-vl0",{0ULL,1ULL,0ULL,2ULL,0ULL,0ULL},0ULL,1ULL,0},
{"lmul-1-vl8",{8ULL,1ULL,0ULL,2ULL,0ULL,0ULL},8ULL,1ULL,0},
{"lmul-2-vl0",{0ULL,2ULL,0ULL,2ULL,0ULL,0ULL},0ULL,2ULL,0},
{"lmul-2-vl8",{8ULL,2ULL,0ULL,2ULL,0ULL,0ULL},8ULL,2ULL,0},
{"lmul-3-vl0",{0ULL,3ULL,0ULL,2ULL,0ULL,0ULL},0ULL,3ULL,0},
{"lmul-3-vl8",{8ULL,3ULL,0ULL,2ULL,0ULL,0ULL},8ULL,3ULL,0},
{"lmul-4-vl0",{0ULL,4ULL,0ULL,2ULL,0ULL,0ULL},0ULL,9223372036854775808ULL,0},
{"lmul-4-vl8",{8ULL,4ULL,0ULL,2ULL,0ULL,0ULL},0ULL,9223372036854775808ULL,0},
{"lmul-5-vl0",{0ULL,5ULL,0ULL,2ULL,0ULL,0ULL},0ULL,5ULL,0},
{"lmul-5-vl8",{8ULL,5ULL,0ULL,2ULL,0ULL,0ULL},2ULL,5ULL,0},
{"lmul-6-vl0",{0ULL,6ULL,0ULL,2ULL,0ULL,0ULL},0ULL,6ULL,0},
{"lmul-6-vl8",{8ULL,6ULL,0ULL,2ULL,0ULL,0ULL},4ULL,6ULL,0},
{"lmul-7-vl0",{0ULL,7ULL,0ULL,2ULL,0ULL,0ULL},0ULL,7ULL,0},
{"lmul-7-vl8",{8ULL,7ULL,0ULL,2ULL,0ULL,0ULL},8ULL,7ULL,0},
{"start-1-vl0-vm0",{0ULL,0ULL,1ULL,2ULL,0ULL,0ULL},0ULL,0ULL,0},
{"start-1-vl0-vm1",{0ULL,0ULL,1ULL,2ULL,0ULL,1ULL},0ULL,0ULL,0},
{"start-1-vl8-vm0",{8ULL,0ULL,1ULL,2ULL,0ULL,0ULL},8ULL,0ULL,0},
{"start-1-vl8-vm1",{8ULL,0ULL,1ULL,2ULL,0ULL,1ULL},8ULL,0ULL,0},
{"start-7-vl0-vm0",{0ULL,0ULL,7ULL,2ULL,0ULL,0ULL},0ULL,0ULL,0},
{"start-7-vl0-vm1",{0ULL,0ULL,7ULL,2ULL,0ULL,1ULL},0ULL,0ULL,0},
{"start-7-vl8-vm0",{8ULL,0ULL,7ULL,2ULL,0ULL,0ULL},8ULL,0ULL,0},
{"start-7-vl8-vm1",{8ULL,0ULL,7ULL,2ULL,0ULL,1ULL},8ULL,0ULL,0},
{"start-127-vl0-vm0",{0ULL,0ULL,127ULL,2ULL,0ULL,0ULL},0ULL,0ULL,0},
{"start-127-vl0-vm1",{0ULL,0ULL,127ULL,2ULL,0ULL,1ULL},0ULL,0ULL,0},
{"start-127-vl8-vm0",{8ULL,0ULL,127ULL,2ULL,0ULL,0ULL},8ULL,0ULL,0},
{"start-127-vl8-vm1",{8ULL,0ULL,127ULL,2ULL,0ULL,1ULL},8ULL,0ULL,0},
{"vs-off-vl0-vm0",{0ULL,0ULL,0ULL,0ULL,0ULL,0ULL},0ULL,0ULL,0},
{"vs-off-vl0-vm1",{0ULL,0ULL,0ULL,0ULL,0ULL,1ULL},0ULL,0ULL,0},
{"vs-off-vl8-vm0",{8ULL,0ULL,0ULL,0ULL,0ULL,0ULL},8ULL,0ULL,0},
{"vs-off-vl8-vm1",{8ULL,0ULL,0ULL,0ULL,0ULL,1ULL},8ULL,0ULL,0},
{"reserved-type-100",{8ULL,256ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"reserved-type-8000000000000000",{8ULL,9223372036854775808ULL,0ULL,2ULL,0ULL,1ULL},0ULL,9223372036854775808ULL,0},
{"encoding-neighbor-1",{8ULL,0ULL,0ULL,2ULL,1ULL,1ULL},8ULL,0ULL,0},
{"encoding-neighbor-2",{8ULL,0ULL,0ULL,2ULL,2ULL,1ULL},8ULL,0ULL,0},
{"legal-after",{8ULL,0ULL,0ULL,2ULL,0ULL,0ULL},8ULL,0ULL,1}};
int main(void) {
  unsigned traps=0;
  for(unsigned i=0;i<64;i++) {
    init(); Result r={0}; const Config *c=&cases[i].cfg;
    unsigned legal=cases[i].legal;
    uint64_t n=exception_case(before,after,c,&r);
    unsigned ok=n==!legal && r.traps==!legal;
    ok &= r.bvl==cases[i].vl && r.btype==cases[i].type && r.bstart==c->start && r.bcsr==7;
    ok &= r.avl==r.bvl && r.atype==r.btype && r.astart==r.bstart && r.acsr==r.bcsr;
    ok &= ((r.status>>9)&3)==(legal?3:c->vs);
    if(!legal) {
      uint32_t word=c->kind==1?0x0220918b:c->kind==2?0x0620818b:c->vm?0x0220818b:0x0020818b;
      ok &= r.cause==2 && r.epc==r.expected_pc && *(const uint32_t*)(uintptr_t)r.epc==word;
      ok &= ((r.trap_status>>9)&3)==c->vs;
      traps++;
    }
    ok &= vectors(3,1,2,c->vm,legal);
    if(!ok) {
      printf("FAIL exception case=%d %s traps=%d cause=%d bvl=%d bstart=%d VS=%d\n",i,cases[i].name,(unsigned)n,(unsigned)r.cause,(unsigned)r.bvl,(unsigned)r.bstart,(unsigned)((r.status>>9)&3));
      return 1;
    }
    printf("PASS exception case=%d %s\n",i,cases[i].name);
  }
  printf("PASS VDOT_EXCEPTIONS cases=64 traps=%d legal=2\n",traps); return 0;
}
