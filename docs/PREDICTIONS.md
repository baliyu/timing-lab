# Predictions, written before any measurement on a board

Date: 2 November 2026. Built with AI assistance (Claude). Nothing in this file has been checked against a measurement; the point is to write down what I expect, with reasons, so that the measurements can prove me wrong.

## Method

The function listings in `asm/` are what `arm-none-eabi-gcc` 13.2.1 makes from `c/compare.c` for a Cortex-M0+ (`-Os`, the Feather M0 build) and a Cortex-M4 (`-O2`, the Nano 33 BLE build). `python/timing_lab/cycles.py` adds up cycles along a path
using the Cortex-M0 manual's instruction table (loads and stores 2 cycles, other simple instructions 1, zero wait states), with taken branches at 2 cycles on the M0+ (3 on the M0, as reported on ARM's forum and the EEVblog; I have not read the M0+ table itself).
It also reports conditional branches that depend on loaded data.

**Caveat that matters:** the boards' own firmware is built with other compiler versions (the Feather with the Arduino core's GCC 9.2.1, the Nano with the Zephyr SDK's GCC 14.3.0). They may produce different loops. Stage 2 reads the compare function out of the real firmware before any measurement; if it differs, I will revise these predictions and say so here, before measuring.

## What the static reading already shows (checked by the tests)

- **cmp_naive** has a branch that depends on the data (the compare of two loaded bytes) on both cores. A matching byte costs **12 cycles** on the M0+ (uxtb, cmp, bhi taken, ldrb, adds, ldrb, cmp, beq taken).
- **cmp_ct**, my secure link's loop, has no branch that depends on the data on either core. One pass costs **13 cycles** on the M0+ whatever the bytes are, so the total depends only on n.
- **cmp_memcmp** has no data branch of its own; it calls `memcmp`, whose code is not in the listing. The boards' libraries decide what it does.

## Predictions to test

| # | Prediction | Basis | What would prove it wrong |
|---|---|---|---|
| P1 | Feather M0, `cmp_naive`: 12 to 20 cycles per matching byte | 12 from the listing with zero wait states (the Feather build's loop is the same code as in `asm/compare_m0plus_Os.lst`); the SAMD21's flash is slower than its 48 MHz core, so wait states are expected, and whether a flash cache hides them in a loop this small is not something I know (not checked) | outside 12 to 20, or not linear in the position of the first difference |
| P2 | Feather M0, `cmp_ct`: the cycle count is the same for every data pattern, within 2 cycles; 13 cycles per byte plus a fixed overhead with zero wait states | no data-dependent branch (checked in the Feather build, which arranges the loop differently from my sandbox build but costs the same 13 cycles per pass); loads are the only data-dependent instructions | a spread above 2 cycles, or a trend with the position of the difference |
| P3 | Feather M0, `cmp_memcmp` (revised, see the log; first written as 3 to 14 cycles per byte, possibly in steps of 4): the library `memcmp` in the Arduino toolchain is a plain byte loop with an early exit, so the cost is linear in the position of the first difference: **11 cycles per matching byte** with zero wait states, up to about 18 with flash wait states, the same for n = 4, 16 and 32 (so a spread across positions of 33 / 165 / 341 cycles at 11 per byte), and no staircase | read from the code in `asm/feather_real.lst`: cmp, bne taken, ldrb, adds, ldrb, cmp, beq taken = 1 + 2 + 2 + 1 + 2 + 1 + 2 | a slope outside 11 to 18, or steps every four bytes |
| P4 | Nano 33 BLE, `cmp_naive`: 8 to 11 cycles per matching byte (revised, see below; first written as 7 to 10) | per byte: cmp 1, branch not taken 1, ldrb 2, ldrb 1 to 2 (pipelined), cmp 1, branch taken 2 to 4 | outside 8 to 11 |
| P5 | Nano, `cmp_ct`: the same count for every data pattern, within 3 cycles | no data-dependent branch; the nRF52840's instruction cache and branch handling are the unknowns | a spread above 3 cycles |
| P6 | Nano, `cmp_memcmp`, with the bench's 4-byte-aligned buffers (revised twice, see the log): the library `memcmp` compares whole 4-byte words and drops to a byte loop only after a word differs, so the cost rises in steps. For n = 4: slope 7 to 10 cycles per byte (about 8), spread across positions 21 to 30. For n = 16: slope 3.0 to 3.9, spread 54 to 72. For n = 32: slope 2.8 to 3.6, spread 98 to 128. The mean at position p + 4 is 11 to 14 cycles above the mean at p | read from the code in `asm/nano_real.lst`: each matching word costs about 12 cycles (two loads, compare, subtract, compare, taken branch), and after a differing word the byte loop costs about 8 cycles per byte (model: 12 per word, 8 per byte inside the word, with 11 to 14 and 7 to 10 as the ranges) | slopes or spreads outside these ranges, or no staircase pattern |
| P7 | The leak is small. For a 4-byte tag, "first byte wrong" against "last byte wrong" differs by about 36 cycles on the Feather (0.75 microseconds at 48 MHz, with zero wait states) and by 21 to 30 cycles on the Nano (about 0.33 to 0.47 microseconds at 64 MHz) | 3 extra bytes times the per-byte cost above | a difference outside these ranges |
| P8 | A Welch t-test between those two classes gives \|t\| above 4.5 for `cmp_naive` and `cmp_memcmp` and below 4.5 for `cmp_ct`, on both boards. If a class has zero variance the test is undefined and I compare the means directly | the usual threshold for calling a timing difference a leak | `cmp_ct` above 4.5, or `cmp_naive` below it |

## What these predictions mean for the real code

- **The MIC check (`ct_equal` in my secure link) should not leak** (P2, P5, P8). Even a leaky compare could not be timed from the radio: the difference is well under a microsecond, while a LoRa packet takes tens of milliseconds on the air and its timing varies by far more. So this lab is about whether the comparison is right, not about a practical attack on the node.
- **The bootloader's digest check uses `memcmp`, which exits early (P3, P6), and that is fine.** The attacker supplies both the image and the stored hash and can compute the SHA-256 themselves, so what leaks is a public value, not a secret. A comparison needs to be constant-time only when one side is secret.

## Revision log

Each revision is made before any measurement on a board; the earlier wording is kept in the git history.

- **Revision 1, 2 November 2026.** I built the Nano bench app in my sandbox (Zephyr 4.4.x, GNU Arm 13.2.1) and read the three comparison functions and `memcmp` out of the firmware (`asm/nano_sandbox_gcc13.lst`, made with `tools/dump_functions.sh`).
  `cmp_naive` and `cmp_ct` are the same loops as in `asm/compare_m4_O2.lst` (checked by a test), so P4 and P5 stand on the same code. The Zephyr build links a byte-by-byte `memcmp` with an early exit, which my first guess for P6 did not allow, so P6 is revised; P4's range is tightened the same way (a taken branch on the M4 costs 2 to 4 cycles).
  This is my sandbox's compiler, not the one that builds the firmware on my own machine (Zephyr SDK, GCC 14.3.0). The same dump is repeated from my own build before the board is run, and any difference is logged here.
- **Revision 2, 2 November 2026.** I read the same functions out of the firmware built on my own machine (Zephyr SDK 1.0.1, GCC 14.3.0; `asm/nano_real.lst`). `cmp_naive`, `cmp_ct` and `cmp_memcmp` are the same instruction sequences as in the sandbox build (checked by a test), so P4 and P5 stand.
  The `memcmp` is not the byte loop of my sandbox build: with both pointers 4-byte aligned it compares a word at a time and falls back to bytes only after a word differs; with either pointer unaligned it uses the byte loop directly. So the "10 to 13 cycles per byte" of revision 1 was wrong for the real build, and P6 is rewritten above. The bench's buffers are aligned,
  so the word path is the one measured; an unaligned run is not part of this lab yet, and a real digest check's alignment depends on where the buffers sit. The sandbox listing is kept as the record of what I first read.
- **Revision 3, 2 November 2026.** I read the same functions out of the Feather M0 firmware built on my own machine (Arduino IDE, Adafruit SAMD core, GCC 9.2.1 from the Arm 9-2019-q4 toolchain; `asm/feather_real.lst`), before running the board. `cmp_naive` and `cmp_memcmp` are the same code as in my sandbox listing, so P1 stands (12 cycles per matching byte).
  `cmp_ct` is arranged differently (a different register order) but has no data-dependent branch and costs the same 13 cycles per pass, so P2 stands. The library `memcmp` is a byte loop with an early exit: my preview from the sandbox's newer newlib showed a word-at-a-time version, which this toolchain does not have, so P3 is rewritten above.
  Predictions for the leak size (P7) on the Feather, with zero wait states: for a 4-byte tag the first byte against the last byte differs by 36 cycles (0.75 microseconds at 48 MHz) in the naive loop and 33 cycles (0.69 microseconds) in `memcmp`. The preview from a newer library was a reminder that the code to read is the code in the build on the board, which is why this stage reads it first.

