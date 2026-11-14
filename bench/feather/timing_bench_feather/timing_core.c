/* timing_core.c - see timing_core.h.  Built with AI assistance (Claude). */
#include "timing_core.h"

const uint8_t timing_lengths[TIMING_NLENGTHS] = {4, 16, 32};

#define WARMUP_CALLS 8u

static uint8_t buf_a[TIMING_MAX_N + 4u] __attribute__((aligned(4)));
static uint8_t buf_b[TIMING_MAX_N + 4u] __attribute__((aligned(4)));

/* ---- tiny text helpers: no printf, so the same lines come out on every board and every C library ---- */
typedef struct { char s[160]; unsigned n; } line_t;

static void put_s(line_t *l, const char *t) { while (*t && l->n < sizeof l->s - 1) l->s[l->n++] = *t++; l->s[l->n] = 0; }

static void put_u64(line_t *l, uint64_t v)
{
  char tmp[21];
  unsigned i = 0;
  do { tmp[i++] = (char)('0' + (unsigned)(v % 10u)); v /= 10u; } while (v);
  while (i && l->n < sizeof l->s - 1) l->s[l->n++] = tmp[--i];
  l->s[l->n] = 0;
}

static void put_field(line_t *l, uint64_t v) { put_s(l, ","); put_u64(l, v); }

unsigned timing_run_off(const timing_platform_t *plat, const timing_fn_t *fns, unsigned nfns, unsigned reps, unsigned run_index, unsigned off)
{
  unsigned total_errors = 0;
  line_t l;
  unsigned f, li, i;
  uint8_t p;
  uint8_t *a, *b;

  if (off > 3u) return 0xFFFFFFFFu;
  a = buf_a + off; b = buf_b + off;

  for (i = 0; i < TIMING_MAX_N; i++) a[i] = (uint8_t)(0x5D + 37u * i);

  l.n = 0; put_s(&l, "BEGIN run "); put_u64(&l, run_index); plat->emit(l.s);

  for (f = 0; f < nfns; f++) {
    for (li = 0; li < TIMING_NLENGTHS; li++) {
      uint8_t n = timing_lengths[li];
      for (p = 0; p <= n; p++) {                      /* p = position of the first difference; p = n: no difference */
        unsigned errors = 0, r, key;
        uint32_t cmin = 0xFFFFFFFFu, cmax = 0;
        uint64_t sum = 0, sumsq = 0;
        int want = (p == n);

        for (i = 0; i < n; i++) b[i] = a[i];
        if (p < n) b[p] = (uint8_t)~a[p];

        for (r = 0; r < WARMUP_CALLS; r++) (void)fns[f].fn(a, b, n);

        for (r = 0; r < reps; r++) {
          uint32_t c0, c1, d;
          int got;
          key = plat->irq_lock();
          c0 = plat->cycles();
          got = fns[f].fn(a, b, n);
          c1 = plat->cycles();
          plat->irq_unlock(key);
          d = c1 - c0;
          if ((got != 0) != (want != 0)) errors++;
          if (d < cmin) cmin = d;
          if (d > cmax) cmax = d;
          sum += d;
          sumsq += (uint64_t)d * d;
        }
        total_errors += errors;

        l.n = 0;
        put_s(&l, "T,"); put_s(&l, fns[f].name);
        put_field(&l, n); put_field(&l, p); put_field(&l, reps); put_field(&l, errors);
        put_field(&l, cmin); put_field(&l, cmax); put_field(&l, sum); put_field(&l, sumsq);
        plat->emit(l.s);
      }
    }
  }

  l.n = 0; put_s(&l, "END run "); put_u64(&l, run_index); plat->emit(l.s);
  return total_errors;
}

unsigned timing_run(const timing_platform_t *plat, const timing_fn_t *fns, unsigned nfns, unsigned reps, unsigned run_index)
{
  return timing_run_off(plat, fns, nfns, reps, run_index, 0u);
}
