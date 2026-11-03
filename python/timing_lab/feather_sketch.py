"""Copies the C sources of the bench into the Arduino sketch folder (bench/feather/timing_bench_feather), because the Arduino IDE only compiles files inside the
sketch folder. A test requires the copies to equal the originals, so they cannot drift.

    PYTHONPATH=python python -m timing_lab.feather_sketch          (run from the repository root)
Built with AI assistance (Claude)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKETCH = ROOT / "bench" / "feather" / "timing_bench_feather"
COPIES = {"compare.c": ROOT / "c" / "compare.c", "compare.h": ROOT / "c" / "compare.h",
          "timing_core.c": ROOT / "bench" / "core" / "timing_core.c", "timing_core.h": ROOT / "bench" / "core" / "timing_core.h"}


def main() -> int:
    SKETCH.mkdir(parents=True, exist_ok=True)
    for name, src in COPIES.items():
        (SKETCH / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        print(f"copied {src.relative_to(ROOT)} -> {(SKETCH / name).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
