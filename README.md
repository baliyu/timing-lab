# timing-lab

Are my own byte comparisons constant-time? A small lab on code from my own repositories: the MIC check in my secure link (`ct_equal`), the digest check in my bootloader (`memcmp`), and a deliberately leaky early-exit loop as a control.
Predictions first, then measurements on a Feather M0 (Cortex-M0+) and a Nano 33 BLE (Cortex-M4F), then a scorecard of what I got right and wrong.

Built with AI assistance (Claude). I chose the question and the code to test, and I read the results; the tools, tests and write-ups were written with Claude. This is a lab on my own code and my own boards, not a security evaluation.

## Status

| Stage | What | State |
|---|---|---|
| 1 | The three functions, the compiler listings, a static reader (cycles along a path, branches that depend on data), predictions written before measuring | **done** ([docs/PREDICTIONS.md](docs/PREDICTIONS.md)) |
| 2 | Read the compare function out of the real firmware build; bench on the Nano 33 BLE | **done** ([docs/SCORECARD.md](docs/SCORECARD.md)): every Nano prediction inside its range |
| 3 | Bench on the Feather M0 (predictions P1 to P3 still to be tested) | in progress: sketch written, compiled against the Feather M0 core and tested; the real build is read next, then the board run |
| 4 | Welch t-test, scorecard against the predictions | not started |
| 5 | README with results and limits | not started |

## What stage 1 shows

On the compiler output for both cores, the early-exit loop has a branch that depends on the data and my secure link's loop has none. A matching byte costs 12 cycles in the early-exit loop on a Cortex-M0+ (zero wait states); one pass of the constant-time loop costs 13 whatever the bytes are.
These are readings of code, not measurements: nothing has run on a board yet.

## What the Nano run showed

On the Nano 33 BLE my secure link's `ct_equal` takes exactly the same number of cycles for every input (86 for a 4-byte tag); the early-exit loop leaks 8 cycles per matching byte and the library `memcmp` leaks in a staircase. Every prediction for the Nano landed inside its range ([docs/SCORECARD.md](docs/SCORECARD.md)).
These are cycle counts with interrupts masked, not a statement about what an attacker could measure.

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
| `bench/core/`, `bench/host/`, `bench/zephyr/` | the portable timing core, a PC program with a fake counter for testing it, and the Nano 33 BLE app |
| `bench/feather/timing_bench_feather/` | the Arduino sketch for the Feather M0 (TC4+TC5 as a cycle counter) with copies of the C files, kept equal by `python/timing_lab/feather_sketch.py` and a test |
| `python/timing_lab/check.py` | reads a bench log: slope per byte, spread, Welch t between "first byte differs" and "last byte differs" |
| `tools/dump_functions.sh` | writes the real machine code of the comparisons out of a built firmware |
| `tests/` | tests on the code, the listings, the bench core (with a fake counter) and the checker, plus a by-hand deliberate-bug check |
| `docs/PREDICTIONS.md` | what I expect, written before any measurement |

## Limits

The listings come from GCC 13.2.1; the boards' builds use other versions and may differ (stage 2 checks this). The cycle costs assume zero wait states and the M0+ costs are not read from the M0+ manual itself.
The data-dependence check is a one-pass reading aid for short functions, not a proof; it follows values loaded from memory and says nothing about caches or other effects. Host timing is not measured: a PC is not the target.

## Running the Nano bench

WSL, the window where the Zephyr environment is active (`source ~/zephyrproject/.venv/bin/activate`; the prompt shows `(.venv)`):

```
cd /mnt/c/timing-lab
export ZEPHYR_BASE=$HOME/zephyrproject/zephyr
west build -p always -b arduino_nano_33_ble -d ~/timing-bench-build bench/zephyr
sh tools/dump_functions.sh ~/timing-bench-build/zephyr/zephyr.elf asm/nano_real.lst
mkdir -p /mnt/c/zephyr_flash && cp ~/timing-bench-build/zephyr/zephyr.bin /mnt/c/zephyr_flash/timing_bench.bin
```

`nano_real.lst` is the real machine code of your own build; check it against the predictions before flashing. Then flash and capture exactly as in dsp-lab (double-tap RESET, `bossac` on the bootloader port, then a PowerShell capture of about 60 seconds from the app's port to `bench/logs/nano_run1.log`), and read it with:

```
PYTHONPATH=python python -m timing_lab.check bench/logs/nano_run1.log
```

## Running the Feather M0 bench

Arduino IDE 2.x, board "Adafruit Feather M0 (SAMD21)", open the folder `bench/feather/timing_bench_feather`, default optimisation. Sketch > Export Compiled Binary writes the `.elf` under `build/` inside that folder.
Read the real machine code of the comparisons out of it with the Arduino toolchain's objdump into `asm/feather_real.lst` (PowerShell commands in the repository's notes for this stage) and check it against the predictions before flashing. Then upload from the IDE, capture about 60 seconds from the Feather's port to `bench/logs/feather_run1.log` as for the Nano, and read it with `python -m timing_lab.check`.

