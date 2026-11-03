/* timing-lab stage 3, board side: Adafruit Feather M0 (ATSAMD21G18, Cortex-M0+, 48 MHz). Built with AI assistance (Claude).

   Runs the same measurement as the Nano 33 BLE (timing_core.c: the three comparisons, three lengths, every position of the first difference, 1000 timed calls each)
   and prints the same log lines over USB serial, so python/timing_lab/check.py reads them in the same way.
   The Cortex-M0+ has no DWT cycle counter, so cycles are counted by the SAMD21's 32-bit timer TC4+TC5, clocked from GCLK0 (the CPU clock, 48 MHz) with no prescaler: one count
   per CPU cycle, the same arrangement as the dsp-lab bench (the rate is checked at start against micros()). Reading that counter takes several cycles of its own (a read
   request and a wait for synchronisation); the log reports the cheapest back-to-back pair of reads as timer_overhead_min_cycles.

   The files next to this sketch (compare.c, compare.h, timing_core.c, timing_core.h) are copies made by python/timing_lab/feather_sketch.py from c/ and bench/core/;
   a test fails if they differ. Open this folder in the Arduino IDE, board "Adafruit Feather M0 (SAMD21)", default optimisation (-Os). */
#include <Arduino.h>

extern "C" {
#include "compare.h"
#include "timing_core.h"
}

#define REPEATS 1000u
#define PAUSE_BETWEEN_RUNS_MS 10000UL

static bool timer_ok = false;
static uint32_t timer_hz = 0;

/* ---- the cycle counter: TC4+TC5 as one 32-bit counter at the CPU clock ---------------------------------------------------------------------- */

static void timer_start(void)
{
    PM->APBCMASK.reg |= PM_APBCMASK_TC4 | PM_APBCMASK_TC5;
    GCLK->CLKCTRL.reg = GCLK_CLKCTRL_CLKEN | GCLK_CLKCTRL_GEN_GCLK0 | GCLK_CLKCTRL_ID(GCM_TC4_TC5);
    while (GCLK->STATUS.bit.SYNCBUSY) { }

    TC4->COUNT32.CTRLA.reg = TC_CTRLA_SWRST;
    while (TC4->COUNT32.CTRLA.bit.SWRST || TC4->COUNT32.STATUS.bit.SYNCBUSY) { }
    TC4->COUNT32.CTRLA.reg = TC_CTRLA_MODE_COUNT32 | TC_CTRLA_PRESCALER_DIV1 | TC_CTRLA_WAVEGEN_NFRQ;
    TC4->COUNT32.CTRLA.reg |= TC_CTRLA_ENABLE;
    while (TC4->COUNT32.STATUS.bit.SYNCBUSY) { }
}

static inline uint32_t timer_now(void)
{
    TC4->COUNT32.READREQ.reg = TC_READREQ_RREQ | TC_READREQ_ADDR(0x10);      /* 0x10 = COUNT */
    while (TC4->COUNT32.STATUS.bit.SYNCBUSY) { }
    return TC4->COUNT32.COUNT.reg;
}

/* ---- the platform for timing_core ---------------------------------------------------------------------------------------------------------- */

static uint32_t plat_cycles(void) { return timer_now(); }

static unsigned plat_irq_lock(void)
{
    unsigned primask = (unsigned)__get_PRIMASK();
    __disable_irq();
    return primask;
}

static void plat_irq_unlock(unsigned primask)
{
    if (primask == 0u) __enable_irq();
}

static void plat_emit(const char *line)
{
    Serial.println(line);
    delay(5);                                   /* the USB serial buffer is small; do not outrun the PC */
}

/* The cheapest possible measurement: two counter reads back to back, so the log shows what reading the counter costs. */
static uint32_t timer_overhead_min(void)
{
    uint32_t best = 0xFFFFFFFFu;
    for (int i = 0; i < 1000; i++) {
        unsigned key = plat_irq_lock();
        uint32_t a = timer_now();
        uint32_t b = timer_now();
        plat_irq_unlock(key);
        if (b - a < best) best = b - a;
    }
    return best;
}

/* ---- run ------------------------------------------------------------------------------------------------------------------------------------ */

void setup(void)
{
    Serial.begin(115200);
    while (!Serial) { }                         /* wait until a terminal opens the port, so the first run is not lost */
    delay(1000);

    timer_start();
    uint32_t t0 = timer_now();
    uint32_t u0 = micros();
    while ((uint32_t)(micros() - u0) < 100000UL) { }                           /* 100 ms by the core's clock */
    uint32_t dt_us = (uint32_t)(micros() - u0);
    uint32_t ticks = timer_now() - t0;
    uint32_t hz = (uint32_t)(((uint64_t)ticks * 1000000ULL) / dt_us);
    timer_ok = (hz > (uint32_t)(F_CPU / 100u * 98u)) && (hz < (uint32_t)(F_CPU / 100u * 102u));
    timer_hz = hz;
}

void loop(void)
{
    static const timing_platform_t plat = { plat_cycles, plat_irq_lock, plat_irq_unlock, plat_emit };
    static const timing_fn_t fns[] = { { "cmp_naive", cmp_naive }, { "cmp_ct", cmp_ct }, { "cmp_memcmp", cmp_memcmp } };
    static unsigned run = 0;

    if (!timer_ok) {
        Serial.println("ERROR: the timer count rate is not within 2% of F_CPU; no benchmark was run");
        delay(2000);
        return;
    }
    Serial.println("ENV board adafruit_feather_m0 (ATSAMD21G18, Cortex-M0+)");
    Serial.print("ENV f_cpu_configured "); Serial.println((unsigned long)F_CPU);
    Serial.print("ENV cpu_hz_measured "); Serial.println((unsigned long)timer_hz);
    Serial.print("ENV arduino_define "); Serial.println((unsigned long)ARDUINO);
    Serial.print("ENV timer_overhead_min_cycles "); Serial.println((unsigned long)timer_overhead_min());
    Serial.print("ENV reps "); Serial.println((unsigned long)REPEATS);
    run++;
    (void)timing_run(&plat, fns, 3, REPEATS, run);
    delay(PAUSE_BETWEEN_RUNS_MS);
}
