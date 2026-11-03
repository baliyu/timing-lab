/* compare.c - the three comparisons measured in this lab.  Built with AI assistance (Claude).
 *
 * cmp_ct is the function ct_equal from secure_link/secure_link.c of github.com/baliyu/stm32l0-freertos-sensor-node
 * (read at commit 046f907), with only the name changed and 'static' removed.  Its three body lines are copied unchanged.
 * cmp_memcmp is the call the bootloader's image check makes (bootloader/image.c).  cmp_naive is the textbook early-exit loop. */
#include <string.h>
#include "compare.h"

int cmp_naive(const uint8_t *a, const uint8_t *b, uint8_t n)
{
  uint8_t i;
  for (i = 0; i < n; i++) if (a[i] != b[i]) return 0;
  return 1;
}

int cmp_ct(const uint8_t *a, const uint8_t *b, uint8_t n)
{
  uint8_t diff = 0, i;
  for (i = 0; i < n; i++) diff |= (uint8_t)(a[i] ^ b[i]);
  return diff == 0;
}

int cmp_memcmp(const uint8_t *a, const uint8_t *b, uint8_t n)
{
  return memcmp(a, b, n) == 0;
}
