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
| P1 | Feather M0, `cmp_naive`: 12 to 20 cycles per matching byte | 12 from the listing with zero wait states; the SAMD21's flash is slower than its 48 MHz core, so wait states are expected (not checked) | outside 12 to 20, or not linear in the position of the first difference |
| P2 | Feather M0, `cmp_ct`: the cycle count is the same for every data pattern, within 2 cycles; total about 13 per byte plus a fixed overhead | no data-dependent branch; loads are the only data-dependent instructions | a spread above 2 cycles, or a trend with the position of the difference |
| P3 | Feather M0, `cmp_memcmp`: exits early; 3 to 14 cycles per byte, possibly in steps of 4 bytes if the library compares words | the code is not in the listing; this is a guess to be replaced by reading the real binary | no early exit at all |
| P4 | Nano 33 BLE, `cmp_naive`: 7 to 10 cycles per matching byte | the M4 pipelines loads and costs a taken branch 2 to 4 cycles; no exact table used | outside 7 to 10 |
| P5 | Nano, `cmp_ct`: the same count for every data pattern, within 3 cycles | no data-dependent branch; the nRF52840's instruction cache and branch handling are the unknowns | a spread above 3 cycles |
| P6 | Nano, `cmp_memcmp`: exits early; 2 to 10 cycles per byte | depends on which C library the build links; to be read from the binary | no early exit |
| P7 | The leak is small. For a 4-byte tag, "first byte wrong" against "last byte wrong" differs by about 36 cycles on the Feather (0.75 microseconds at 48 MHz, with zero wait states) and by 21 to 30 cycles on the Nano (about 0.33 to 0.47 microseconds at 64 MHz) | 3 extra bytes times the per-byte cost above | a difference outside these ranges |
| P8 | A Welch t-test between those two classes gives \|t\| above 4.5 for `cmp_naive` and `cmp_memcmp` and below 4.5 for `cmp_ct`, on both boards. If a class has zero variance the test is undefined and I compare the means directly | the usual threshold for calling a timing difference a leak | `cmp_ct` above 4.5, or `cmp_naive` below it |

## What these predictions mean for the real code

- **The MIC check (`ct_equal` in my secure link) should not leak** (P2, P5, P8). Even a leaky compare could not be timed from the radio: the difference is well under a microsecond, while a LoRa packet takes tens of milliseconds on the air and its timing varies by far more. So this lab is about whether the comparison is right, not about a practical attack on the node.
- **The bootloader's digest check uses `memcmp`, which exits early (P3, P6), and that is fine.** The attacker supplies both the image and the stored hash and can compute the SHA-256 themselves, so what leaks is a public value, not a secret. A comparison needs to be constant-time only when one side is secret.
