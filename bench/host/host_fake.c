/* host_fake.c - runs the bench core on the PC with a fake cycle counter, to test the core and the checker (it measures nothing real).
 *   ./host_fake fixed       every call to a comparison "takes" 7 cycles, whatever it is given
 *   ./host_fake model       synthetic functions with a known cost: leaky costs 12 cycles per matching byte, constant costs 13 per byte of n */
#include <stdio.h>
#include <string.h>
#include "timing_core.h"
#include "compare.h"

static uint32_t fake_now;
static uint32_t fake_cycles(void) { uint32_t t = fake_now; fake_now += 1; return t; }       /* each read costs one cycle */
static unsigned fake_lock(void) { return 0; }
static void fake_unlock(unsigned k) { (void)k; }
static void fake_emit(const char *line) { puts(line); }

static int fixed_fn(const uint8_t *a, const uint8_t *b, uint8_t n) { fake_now += 7; return cmp_ct(a, b, n); }

static int leaky_fn(const uint8_t *a, const uint8_t *b, uint8_t n)
{
  uint8_t i;
  fake_now += 5;
  for (i = 0; i < n; i++) { fake_now += 12; if (a[i] != b[i]) return 0; }
  return 1;
}

static int constant_fn(const uint8_t *a, const uint8_t *b, uint8_t n) { fake_now += 5u + 13u * n; return cmp_ct(a, b, n); }

int main(int argc, char **argv)
{
  static const timing_platform_t plat = {fake_cycles, fake_lock, fake_unlock, fake_emit};
  timing_fn_t fixed[] = {{"cmp_naive", fixed_fn}, {"cmp_ct", fixed_fn}, {"cmp_memcmp", fixed_fn}};
  timing_fn_t model[] = {{"cmp_naive", leaky_fn}, {"cmp_ct", constant_fn}};
  unsigned errors;
  if (argc > 1 && strcmp(argv[1], "model") == 0) errors = timing_run(&plat, model, 2, 50, 1);
  else errors = timing_run(&plat, fixed, 3, 50, 1);
  fprintf(stderr, "errors %u\n", errors);
  return errors ? 1 : 0;
}
