"""Builds c/compare.c into a shared library with the host C compiler and exposes the three functions to Python (for functional tests only: host timing is not what this lab measures)."""
from __future__ import annotations

import ctypes
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(outdir=None):
    out = Path(outdir or tempfile.mkdtemp()) / "libcompare.so"
    subprocess.run(["gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", str(ROOT / "c"), str(ROOT / "c" / "compare.c"), "-o", str(out)], check=True)
    return out


def load(path=None):
    lib = ctypes.CDLL(str(path or build()))
    fns = {}
    for name in ("cmp_naive", "cmp_ct", "cmp_memcmp"):
        f = getattr(lib, name)
        f.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint8]
        f.restype = ctypes.c_int
        fns[name] = f
    return fns
