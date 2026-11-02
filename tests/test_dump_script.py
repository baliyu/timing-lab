import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "dump_functions.sh"
needs_arm = pytest.mark.skipif(shutil.which("arm-none-eabi-gcc") is None or shutil.which("arm-none-eabi-objdump") is None, reason="no ARM toolchain")


def run(args, env_extra=None, path=None):
    env = dict(os.environ, **(env_extra or {}))
    if path is not None:
        env["PATH"] = path
    return subprocess.run(["/bin/sh", str(SCRIPT)] + args, capture_output=True, text=True, env=env)


@needs_arm
def test_the_script_writes_a_listing_with_the_comparison_functions_from_a_built_object(tmp_path):
    obj = tmp_path / "compare.o"
    subprocess.run(["arm-none-eabi-gcc", "-mcpu=cortex-m4", "-mthumb", "-O2", "-c", str(ROOT / "c" / "compare.c"), "-o", str(obj)], check=True)
    out = tmp_path / "out.lst"
    r = run([str(obj), str(out)], {"OBJDUMP": shutil.which("arm-none-eabi-objdump")})
    assert r.returncode == 0, r.stdout + r.stderr
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# built by:") and "# firmware: compare.o" in text
    for name in ("<cmp_naive>:", "<cmp_ct>:", "<cmp_memcmp>:"):
        assert name in text
    assert "using " in r.stdout and "wrote" in r.stdout


@needs_arm
def test_the_script_refuses_a_file_that_does_not_contain_the_comparisons(tmp_path):
    src = tmp_path / "other.c"
    src.write_text("int f(int x) { return x + 1; }\n")
    obj = tmp_path / "other.o"
    subprocess.run(["arm-none-eabi-gcc", "-mcpu=cortex-m4", "-mthumb", "-c", str(src), "-o", str(obj)], check=True)
    r = run([str(obj), str(tmp_path / "o.lst")], {"OBJDUMP": shutil.which("arm-none-eabi-objdump")})
    assert r.returncode == 1 and "only" in r.stdout


def test_the_script_says_how_to_fix_a_missing_objdump(tmp_path):
    f = tmp_path / "x.elf"
    f.write_bytes(b"x")
    r = run([str(f), str(tmp_path / "o.lst")], {"HOME": str(tmp_path), "OBJDUMP": ""}, path="/bin:/usr/bin" if not shutil.which("arm-none-eabi-objdump") else "/nonexistent")
    assert r.returncode == 1 and "no objdump found" in r.stdout


def test_the_script_with_no_arguments_prints_its_usage():
    r = run([])
    assert r.returncode == 1 and "usage" in r.stdout
