#ifndef COMPARE_H
#define COMPARE_H
#include <stdint.h>

/* Three ways to ask "are these n bytes equal?". All return 1 if equal, 0 if not. */
int cmp_naive(const uint8_t *a, const uint8_t *b, uint8_t n);    /* stops at the first difference (a deliberately leaky control) */
int cmp_ct(const uint8_t *a, const uint8_t *b, uint8_t n);       /* the loop my secure link uses: always reads all n bytes */
int cmp_memcmp(const uint8_t *a, const uint8_t *b, uint8_t n);   /* what my bootloader uses for the image digest */

#endif
