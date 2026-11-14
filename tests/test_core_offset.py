"""timing_run_off hands the comparison functions pointers with the requested alignment. Built with AI assistance (Claude)."""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
C_SRC = r'''
#include <stdio.h>
#include <stdint.h>
#include "timing_core.h"
static uint32_t t;
static uint32_t cy(void) { return t++; }
static unsigned lk(void) { return 0; }
static void ul(unsigned k) { (void)k; }
static void em(const char *l) { (void)l; }
static unsigned bad, calls;
static int chk(const uint8_t *a, const uint8_t *b, uint8_t n)
{
  uint8_t i;
  calls++;
  if (((uintptr_t)a & 3u) != WANT || ((uintptr_t)b & 3u) != WANT) bad++;
  for (i = 0; i < n; i++) if (a[i] != b[i]) return 0;
  return 1;
}
int main(void)
{
  timing_platform_t p = {cy, lk, ul, em};
  timing_fn_t f[] = {{"chk", chk}};
  unsigned e = timing_run_off(&p, f, 1, 3, 1, OFF);
  printf("%u %u %u\n", e, bad, calls);
  return 0;
}
'''


def run(tmp_path, want, off):
    src = tmp_path / "t.c"
    src.write_text(C_SRC)
    exe = tmp_path / "t"
    subprocess.run(["gcc", "-std=c99", "-Wall", "-DWANT=%d" % want, "-DOFF=%d" % off, "-I", str(ROOT / "bench" / "core"),
                    str(src), str(ROOT / "bench" / "core" / "timing_core.c"), "-o", str(exe)], check=True)
    return subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout.split()


@pytest.mark.parametrize("off", [0, 1, 2, 3])
def test_pointers_have_the_requested_alignment(tmp_path, off):
    errors, bad, calls = run(tmp_path, off, off)
    assert errors == "0" and bad == "0" and int(calls) > 0


def test_an_offset_above_three_runs_nothing(tmp_path):
    errors, bad, calls = run(tmp_path, 0, 4)
    assert errors == "4294967295" and calls == "0"
