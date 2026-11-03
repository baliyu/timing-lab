# Scorecard: predictions against the first Nano 33 BLE run

Built with AI assistance (Claude). Predictions are in [PREDICTIONS.md](PREDICTIONS.md) (revision 2, written before the board was run); the capture is `bench/logs/nano_run1.log`. `tests/test_scorecard_nano.py` checks every row below against the log, so this page cannot drift from the data.
The Feather M0 predictions (P1 to P3) have not been measured yet.

## The run

Arduino Nano 33 BLE (nRF52840, Cortex-M4F), Zephyr 4.4.2, firmware built with the Zephyr SDK 1.0.1 compiler (GCC 14.3.0), CPU clock measured at 63.99 MHz, interrupts masked around each timed call, 1000 timed calls per case, 5 complete runs, no damaged lines, no wrong answers.
**Every one of the 165 cases was perfectly repeatable: the same cycle count on all 1000 calls, and the same in all 5 runs.** With no variation at all, the Welch t is undefined; the checker reports an infinite t when two such cases differ and 0 when they are identical.

## Results

| Function | n | Cycles when the first difference is at byte 0 | at the last byte | Slope (cycles per byte) |
|---|---|---|---|---|
| `cmp_ct` (my secure link's loop) | 4 / 16 / 32 | 86 / 182 / 310 | the same | 0 |
| `cmp_naive` (early exit) | 4 / 16 / 32 | 55 | 79 / 175 / 303 | 8.00 |
| `cmp_memcmp` (the library, aligned buffers) | 4 / 16 / 32 | 92 | 116 / 149 / 193 | 8.00 / 3.06 / 2.83 |

## Predictions against measurements

| # | Predicted | Measured | Verdict |
|---|---|---|---|
| P4 | naive loop: 8 to 11 cycles per matching byte | 8.00 at every length | hit, at the bottom of the range |
| P5 | constant-time loop: the same count whatever the data, within 3 cycles | spread 0.00; 86, 182 and 310 cycles for 4, 16 and 32 bytes, so 8.0 cycles per byte | hit, exactly |
| P6 | `memcmp`: slope 7 to 10 / 3.0 to 3.9 / 2.8 to 3.6 and spread 21 to 30 / 54 to 72 / 98 to 128 for n = 4 / 16 / 32; a step of 11 to 14 cycles per four bytes | slope 8.00 / 3.06 / 2.83; spread 24 / 57 / 101; every step exactly 11, and 8 per byte inside a word | hit on every range; two sit at the lower edge (the 2.83 slope, the step of 11), because my model's 12 cycles per word was one cycle high |
| P7 | for a 4-byte tag, first byte against last byte differs by 21 to 30 cycles | 24 cycles = 0.375 microseconds | hit |
| P8 | \|t\| above 4.5 for the naive loop and `memcmp`, below 4.5 for the constant-time loop | infinite (no variance, means differ) for both early-exit functions, 0 for `cmp_ct` | hit |

Two earlier guesses were wrong and were corrected before the run, both because I had read the wrong code: revision 1 assumed a byte-loop `memcmp` (my sandbox's library), and my own build's library compares words first.

## What it shows

- **The secure link's comparison does what it is meant to.** On this build, `ct_equal` takes exactly the same time whether the strings are equal or differ at any byte: 86 cycles for a 4-byte tag, in all 5 runs.
- **Early exit leaks exactly, with no noise to hide it.** The naive loop leaks 8 cycles per matching byte; the library `memcmp` leaks in a staircase (8 cycles per byte inside a four-byte word, 11 per whole word before it).
- **The constant-time loop costs nothing extra here.** At n = 32 it takes 310 cycles, against 307 for the naive loop's worst case.

## What it does not show

One board, one compiler, one set of aligned buffers: with an unaligned pointer this `memcmp` takes its byte loop, and I have not run that. Interrupts were masked and nothing else was running, which is why there is no noise at all; a real attacker faces whatever noise sits between them and the comparison.
A 4-byte tag leaks 0.375 microseconds here, and I have not argued whether that could be used from a radio (my argument is in the predictions, and it is an argument, not a measurement). Nothing here says whether the leak of `memcmp` in the bootloader matters: it compares a public value.
The Feather M0 (a Cortex-M0+ with no cache and slower flash) is next.
