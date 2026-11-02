#include <stdint.h>
#include <klib.h>

extern unsigned long vdot_case(const int8_t *, const int8_t *, const uint8_t *,
                               uint8_t *, const uint8_t *, unsigned long, unsigned long);
static int8_t a[16] __attribute__((aligned(16)));
static int8_t b[16] __attribute__((aligned(16)));
static uint8_t old[16] __attribute__((aligned(16)));
static uint8_t out[16] __attribute__((aligned(16)));
static uint8_t mask[2] __attribute__((aligned(16)));

int main(void) {
  for (unsigned c = 0; c < 7; ++c) {
    unsigned vl = c == 5 ? 0 : c == 6 ? 16 : 8;
    unsigned vm = c == 3 || c == 4 ? 0 : 1;
    mask[0] = c == 4 ? 0 : 0x55; mask[1] = 0xff;
    for (unsigned i = 0; i < 16; ++i) {
      a[i] = i >= 8 ? 127 : c == 1 || c == 2 ? -128 : (int)i + 1;
      b[i] = i >= 8 ? -128 : c == 1 ? -128 : c == 2 ? 127 : 1;
      old[i] = 0xa0 + i; out[i] = 0xee;
    }
    int32_t sum = 0;
    for (unsigned i = 0; i < 8; ++i)
      if (vm || ((mask[0] >> i) & 1)) sum += (int32_t)a[i] * (int32_t)b[i];
    unsigned long status = vdot_case(a,b,old,out,mask,vl,vm);
    if ((status & 255) != vl || ((status >> 8) & 3) != 3) {
      printf("FAIL vdot case=%d VL/VS status=%x\n", c, (unsigned)status); return 1;
    }
    for (unsigned i = 0; i < 16; ++i) {
      uint8_t expected = vl == 0 ? old[i] : i < 4 ? (uint32_t)sum >> (8*i) : 0;
      if (out[i] != expected) {
        printf("FAIL vdot case=%d byte=%d got=%x expected=%x\n",c,i,out[i],expected); return 1;
      }
    }
    unsigned long vcsr, vstart;
    __asm__ volatile("csrr %0, vcsr" : "=r"(vcsr));
    __asm__ volatile("csrr %0, vstart" : "=r"(vstart));
    if (vcsr != 7 || vstart != 0) { printf("FAIL vdot CSR preservation\n"); return 1; }
    printf("PASS vdot case=%d vl=%d vm=%d sum=%d full128=OK VS=Dirty\n",c,vl,vm,sum);
  }
  printf("PASS VDOT_SMOKE cases=7\n");
  return 0;
}
