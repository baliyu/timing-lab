# timing-lab

Are my own byte comparisons constant-time? A small lab on code from my own repositories: the MIC check in my secure link (`ct_equal`), the digest check in my bootloader (`memcmp`), and a deliberately leaky early-exit loop as a control.
Predictions first, then measurements on a Feather M0 (Cortex-M0+) and a Nano 33 BLE (Cortex-M4F), then a scorecard of what I got right and wrong.

Built with AI assistance (Claude). I chose the question and the code to test, and I read the results; the tools, tests and write-ups were written with Claude. This is a lab on my own code and my own boards, not a security evaluation.

## Status

| Stage | What | State |
|---|---|---|
| 1 | The three functions, the compiler listings, a static reader (cycles along a path, branches that depend on data), predictions written before measuring | **done** ([docs/PREDICTIONS.md](docs/PREDICTIONS.md)) |
| 2 | Read the compare function out of the real firmware builds; bench on the Nano 33 BLE | not started |
| 3 | Bench on the Feather M0 | not started |
| 4 | Welch t-test, scorecard against the predictions | not started |
| 5 | README with results and limits | not started |

## What stage 1 shows

On the compiler output for both cores, the early-exit loop has a branch that depends on the data and my secure link's loop has none. A matching byte costs 12 cycles in the early-exit loop on a Cortex-M0+ (zero wait states); one pass of the constant-time loop costs 13 whatever the bytes are.
These are readings of code, not measurements: nothing has run on a board yet.

## Use

```
pip install -r requirements.txt
pytest -q
sh tools/make_listings.sh     # needs arm-none-eabi-gcc; rebuilds asm/*.lst
```

## What is where

| Path | What it is |
|---|---|
| `c/compare.[ch]` | the three comparisons; `cmp_ct` is `ct_equal` from my secure link, body unchanged |
| `asm/` | the Thumb listings the compiler makes, with the compiler version and flags in the first lines |
| `python/timing_lab/cycles.py` | cycles along a path (Cortex-M0+ costs), and the check for branches that depend on loaded data |
| `python/timing_lab/hostlib.py` | builds the C file for the PC so the three functions can be tested for correctness |
| `tests/` | 34 tests on the code and the listings, plus a by-hand deliberate-bug check |
| `docs/PREDICTIONS.md` | what I expect, written before any measurement |

## Limits

The listings come from GCC 13.2.1; the boards' builds use other versions and may differ (stage 2 checks this). The cycle costs assume zero wait states and the M0+ costs are not read from the M0+ manual itself.
The data-dependence check is a one-pass reading aid for short functions, not a proof; it follows values loaded from memory and says nothing about caches or other effects. Host timing is not measured: a PC is not the target.
