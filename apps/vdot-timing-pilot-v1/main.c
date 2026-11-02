#include <stdint.h>
#include <klib.h>
typedef void (*Fn)(const void*,void*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
extern void pilot_empty(const void*,void*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
extern void pilot_addi16(const void*,void*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
extern void pilot_addi64(const void*,void*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
extern void pilot_native(const void*,void*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
extern void pilot_rvv_m1(const void*,void*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
extern void pilot_rvv_mf2(const void*,void*,uint64_t*,uint64_t,uint64_t,uint64_t,uint64_t);
static Fn funcs[]={pilot_empty,pilot_addi16,pilot_addi64,pilot_native,pilot_rvv_m1,pilot_rvv_mf2};
static const uint8_t input[4][16] __attribute__((aligned(16)))={{0xffULL,0xa0ULL,0xa1ULL,0xa2ULL,0xa3ULL,0xa4ULL,0xa5ULL,0xa6ULL,0xa7ULL,0xa8ULL,0xa9ULL,0xaaULL,0xabULL,0xacULL,0xadULL,0xaeULL},{0x1ULL,0x2ULL,0x3ULL,0x4ULL,0x5ULL,0x6ULL,0x7ULL,0x8ULL,0x90ULL,0x97ULL,0x9eULL,0xa5ULL,0xacULL,0xb3ULL,0xbaULL,0xc1ULL},{0x1ULL,0x1ULL,0x1ULL,0x1ULL,0x1ULL,0x1ULL,0x1ULL,0x1ULL,0x60ULL,0x6bULL,0x76ULL,0x81ULL,0x8cULL,0x97ULL,0xa2ULL,0xadULL},{0x24ULL,0xb2ULL,0xbfULL,0xccULL,0xd9ULL,0xe6ULL,0xf3ULL,0x0ULL,0xdULL,0x1aULL,0x27ULL,0x34ULL,0x41ULL,0x4eULL,0x5bULL,0x68ULL}};
static const uint64_t expected[6][4][2]={{{0xa6a5a4a3a2a1a0ffULL,0xaeadacabaaa9a8a7ULL},{0x807060504030201ULL,0xc1bab3aca59e9790ULL},{0x101010101010101ULL,0xada2978c81766b60ULL},{0xf3e6d9ccbfb224ULL,0x685b4e4134271a0dULL}},{{0xa6a5a4a3a2a1a0ffULL,0xaeadacabaaa9a8a7ULL},{0x807060504030201ULL,0xc1bab3aca59e9790ULL},{0x101010101010101ULL,0xada2978c81766b60ULL},{0xf3e6d9ccbfb224ULL,0x685b4e4134271a0dULL}},{{0xa6a5a4a3a2a1a0ffULL,0xaeadacabaaa9a8a7ULL},{0x807060504030201ULL,0xc1bab3aca59e9790ULL},{0x101010101010101ULL,0xada2978c81766b60ULL},{0xf3e6d9ccbfb224ULL,0x685b4e4134271a0dULL}},{{0xa6a5a4a3a2a1a0ffULL,0xaeadacabaaa9a8a7ULL},{0x807060504030201ULL,0xc1bab3aca59e9790ULL},{0x101010101010101ULL,0xada2978c81766b60ULL},{0x24ULL,0x0ULL}},{{0xa6a5a4a3a2a1a0ffULL,0xaeadacabaaa9a8a7ULL},{0x807060504030201ULL,0xc1bab3aca59e9790ULL},{0x101010101010101ULL,0xada2978c81766b60ULL},{0x24ULL,0x0ULL}},{{0xa6a5a4a3a2a1a0ffULL,0xaeadacabaaa9a8a7ULL},{0x807060504030201ULL,0xc1bab3aca59e9790ULL},{0x101010101010101ULL,0xada2978c81766b60ULL},{0x24ULL,0x0ULL}}};
static const unsigned expected_inst[]={4,20,68,5,13,13};
static uint64_t out[4][2] __attribute__((aligned(16)));
static uint64_t meta[15];
int main(void) {
 unsigned count=0;
 for(unsigned round=0;round<7;round++) for(unsigned pos=0;pos<6;pos++) {
  unsigned k=round==0?pos:(pos+round-1)%6;
  for(unsigned r=0;r<4;r++) for(unsigned w=0;w<2;w++) out[r][w]=0xeeeeeeeeeeeeeeeeULL;
  for(unsigned j=0;j<15;j++) meta[j]=0;
  funcs[k](input,out,meta,8,0,3,5);
  uint64_t cycles=meta[9]-meta[6], retired=meta[8]-meta[7];
  if(cycles>0x7fffffffULL || retired>0x7fffffffULL) {printf("FAIL PILOT_COUNTER_RANGE variant=%d\n",k);return 1;}
  printf("PERF_SAMPLE warm=%d round=%d position=%d variant=%d cycles=%d instret=%d consumer=%d\n",round==0,round,pos,k,(unsigned)cycles,(unsigned)retired,(unsigned)meta[10]);
  for(unsigned r=0;r<4;r++) for(unsigned w=0;w<2;w++) if(out[r][w]!=expected[k][r][w]) {
   printf("FAIL PILOT_VECTOR variant=%d reg=%d word=%d\n",k,r,w);return 1;
  }
  if(((meta[0]>>9)&3)!=3 || meta[1]!=8 || meta[2]!=0 || meta[3]!=0 || meta[4]!=3 || meta[5]!=5 || meta[10]!=36 || meta[12]!=meta[14]) {
   printf("FAIL PILOT_STATE variant=%d\n",k);return 1;
  }
  unsigned addi=k==1?16:k==2?64:0;
  if(meta[11]!=addi || (meta[13]&5)!=0 || cycles==0 || retired!=expected_inst[k]) {
   printf("FAIL PILOT_CALIBRATION variant=%d got_instret=%d expected_instret=%d inhibit=%d\n",k,(unsigned)retired,expected_inst[k],(unsigned)meta[13]);return 1;
  }
  count++;
 }
 printf("PASS VDOT_TIMING_PILOT calls=%d samples=36 warmups=6 variants=6 full128=1 state=1\n",count);
 return 0;
}
