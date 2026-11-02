#include <stdint.h>
#include <klib.h>

// Standard RISC-V calling convention: a0=A, a1=B, a2=C, a3=requested count.
extern unsigned long vadd4(const int32_t *a, const int32_t *b,
                           int32_t *c, unsigned long count);

static const int32_t a[4] __attribute__((aligned(16))) = {1, 2, 3, 4};
static const int32_t b[4] __attribute__((aligned(16))) = {10, 20, 30, 40};
static int32_t c[4] __attribute__((aligned(16))) = {-1, -1, -1, -1};
static const int32_t expected[4] = {11, 22, 33, 44};

int main(void) {
    unsigned long vl = vadd4(a, b, c, 4);
    unsigned long vlenb;
    __asm__ volatile("csrr %0, vlenb" : "=r"(vlenb));
    printf("vadd4: VL=%d SEW=32 LMUL=1 VLEN=%d bits\n",
           (int)vl, (int)(vlenb * 8));
    if (vl != 4) {
        printf("FAIL: expected VL=4, got %d\n", (int)vl);
        return 1;
    }
    for (int i = 0; i < 4; ++i) {
        printf("C[%d] = %d (expected %d)\n", i, (int)c[i], (int)expected[i]);
        if (c[i] != expected[i]) {
            printf("FAIL: element %d mismatch\n", i);
            return 1;
        }
    }
    printf("PASS: vadd.vv produced [11, 22, 33, 44]\n");
    return 0;
}
