# Scorecard: predictions against the Nano 33 BLE and Feather M0 runs

Built with AI assistance (Claude). Predictions are in [PREDICTIONS.md](PREDICTIONS.md) (the Nano ones from revision 2, the Feather ones from revision 3, each written after reading the code in my own build and before running the board); the captures are `bench/logs/nano_run1.log` and `bench/logs/feather_run1.log`.
`tests/test_scorecard_nano.py` and `tests/test_scorecard_feather.py` check every row below against the logs, so this page cannot drift from the data.

## Arduino Nano 33 BLE (Cortex-M4F)

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

## Adafruit Feather M0 (Cortex-M0+)

### The run

Feather M0 (ATSAMD21G18), Arduino IDE with the Adafruit SAMD core, GCC 9.2.1 (Arm 9-2019-q4 toolchain), default -Os, CPU clock measured at 48.001 MHz against `micros()`, interrupts masked around each timed call, cycles counted by timer TC4+TC5 at the CPU clock, 1000 timed calls per case, 5 complete runs, no damaged lines, no wrong answers.
Reading the counter costs 36 cycles by itself (the log reports it), so absolute counts include that; differences between cases do not.
`cmp_ct` was perfectly repeatable. In all 110 cases of the two early-exit functions exactly one of the 1000 calls took one cycle less than the rest (in 3 cases of a later run, none did); I did not investigate why.

| Function | n | Cycles when the first difference is at byte 0 | at the last byte | Slope (cycles per byte) |
|---|---|---|---|---|
| `cmp_ct` | 4 / 16 / 32 | 144 / 300 / 508 | the same | 0 |
| `cmp_naive` | 4 / 16 / 32 | 101 | 137 / 281 / 473 | 12.00 |
| `cmp_memcmp` | 4 / 16 / 32 | 110 | 144 / 276 / 452 | 11.30 / 11.02 / 11.01 |

### Predictions against measurements

| # | Predicted | Measured | Verdict |
|---|---|---|---|
| P1 | naive loop: 12 to 20 cycles per matching byte | 12.00 at every length | hit, at the bottom: the flash wait states I expected to slow the loop did not show; why, I did not investigate |
| P2 | constant-time loop: the same count whatever the data, within 2 cycles; 13 cycles per byte | spread 0.00; 144, 300 and 508 cycles for 4, 16 and 32 bytes, so 13.0 per byte | hit, exactly |
| P3 | `memcmp`: a plain byte loop, 11 to 18 cycles per byte, spread 33 / 165 / 341 cycles for n = 4 / 16 / 32, no staircase | slope 11.30 / 11.02 / 11.01, spread 34 / 166 / 342, no staircase | the slope and the shape hit; **the three spreads missed by one cycle each**, because the first matching byte costs 12 cycles instead of 11 (every other step is exactly 11). I did not find why |
| P7 | 4-byte tag, first byte against last: 36 cycles (0.75 microseconds) for the naive loop, 33 (0.69) for `memcmp` | 36 cycles (0.750 microseconds) and 34 (0.708) | naive: hit. `memcmp`: missed by one cycle |
| P8 | \|t\| above 4.5 for the naive loop and `memcmp`, below 4.5 for the constant-time loop | t from 24,000 to 263,000 for the early-exit functions, 0 for `cmp_ct` | hit |

My preview of the Feather's `memcmp`, from the newer library in my sandbox, showed a word-at-a-time version; the Arduino toolchain's library is a byte loop. I caught that by reading the code in the real build before the run, and the predictions were rewritten first.

## Across the two boards

The same source line, `memcmp(a, b, n)`, leaks differently on each board, because the library behind it differs. The constant-time loop is constant on both.

| Cycles per byte | Nano 33 BLE (Cortex-M4F) | Feather M0 (Cortex-M0+) |
|---|---|---|
| `cmp_ct` | 8, same for every input | 13, same for every input |
| `cmp_naive`, per matching byte | 8 | 12 |
| `cmp_memcmp` | a staircase: 11 per four-byte word, 8 per byte inside the word | linear: 11 per byte (the first byte 12) |

## What it shows

- **`ct_equal` does what it is meant to on both boards.** It takes the same number of cycles for every input on a Cortex-M4F and a Cortex-M0+. The secure link's real target, the STM32L072, is also a Cortex-M0+, but I did not measure it and I do not touch that chip's locked build.
- **What a library `memcmp` leaks is a property of the toolchain, not of the line of C.** The bootloader compares a public digest, so this does not matter there; it would matter for a secret.
- **The constant-time loop costs little.** At n = 32 it takes 310 cycles on the Nano against 307 for the naive loop's worst case, and 508 on the Feather against 473.

## What it does not show

One board of each kind, one compiler each, buffers aligned to four bytes (an unaligned pointer sends the Nano's `memcmp` to its byte loop, and I have not run that), interrupts masked and nothing else running, which is why there is almost no noise.
A real attacker faces whatever noise sits between them and the comparison, and I have not argued from these numbers that a leak of this size could be used over a radio. The first Nano capture and the first Feather capture are one capture each (five runs each, identical apart from the one-cycle variation noted above).
I did not measure the STM32L072, other compiler versions or optimisation levels, or the effect of interrupts being enabled.

