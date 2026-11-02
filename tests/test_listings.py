"""The committed listings are what the compiler makes from c/compare.c (checked only when the same compiler version is installed)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def header_version(name):
    return (ROOT / "asm" / name).read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()


def test_the_listings_say_which_compiler_made_them_and_how():
    for name in ("compare_m0plus_Os.lst", "compare_m4_O2.lst"):
        first = (ROOT / "asm" / name).read_text(encoding="utf-8").splitlines()[:2]
        assert first[0].startswith("# arm-none-eabi-gcc") and "-mcpu=" in first[1] and "-mthumb" in first[1]


@pytest.mark.skipif(shutil.which("arm-none-eabi-gcc") is None, reason="no ARM compiler installed")
def test_the_listings_match_a_fresh_build_when_the_compiler_version_is_the_same(tmp_path):
    ver = subprocess.run(["arm-none-eabi-gcc", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    if ver != header_version("compare_m0plus_Os.lst"):
        pytest.skip(f"compiler is {ver!r}, the listings were made with {header_version('compare_m0plus_Os.lst')!r}")
    for cpu, opt, name in (("cortex-m0plus", "Os", "compare_m0plus_Os.lst"), ("cortex-m4", "O2", "compare_m4_O2.lst")):
        obj = tmp_path / f"{cpu}.o"
        subprocess.run(["arm-none-eabi-gcc", f"-mcpu={cpu}", "-mthumb", f"-{opt}", "-c", str(ROOT / "c" / "compare.c"), "-o", str(obj)], check=True)
        dis = subprocess.run(["arm-none-eabi-objdump", "-d", "--no-show-raw-insn", str(obj)], capture_output=True, text=True, check=True).stdout.splitlines()[3:]
        committed = (ROOT / "asm" / name).read_text(encoding="utf-8").splitlines()[2:]
        assert dis == committed, name
