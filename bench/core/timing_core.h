#ifndef TIMING_CORE_H
#define TIMING_CORE_H
/* The part of the timing bench that does not depend on the board: which cases to run, how to time them, and the text lines it prints.
   The board supplies a cycle counter, interrupt masking and a way to print a line (see bench/zephyr/src/main.c). */
#include <stddef.h>
#include <stdint.h>

typedef struct {
  uint32_t (*cycles)(void);          /* a free-running cycle counter */
  unsigned (*irq_lock)(void);        /* mask interrupts, return a key */
  void (*irq_unlock)(unsigned key);
  void (*emit)(const char *line);    /* print one line (no newline in the string) */
} timing_platform_t;

typedef int (*timing_cmp_fn)(const uint8_t *a, const uint8_t *b, uint8_t n);
typedef struct { const char *name; timing_cmp_fn fn; } timing_fn_t;

#define TIMING_MAX_N 32u
#define TIMING_NLENGTHS 3u
extern const uint8_t timing_lengths[TIMING_NLENGTHS];   /* 4 (a MIC), 16, 32 (a SHA-256 digest) */

/* One pass over every function, every length n and every position p of the first difference (p = n means the strings are equal).
   Prints  BEGIN run <k> ... T,<function>,<n>,<p>,<reps>,<errors>,<min>,<max>,<sum>,<sumsq> ... END run <k>.
   Returns the number of calls that gave the wrong answer (it should be 0). */
unsigned timing_run(const timing_platform_t *plat, const timing_fn_t *fns, unsigned nfns, unsigned reps, unsigned run_index);

#endif
