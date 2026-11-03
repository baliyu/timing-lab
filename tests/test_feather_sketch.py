import shutil
import subprocess
from pathlib import Path

import pytest

from timing_lab import feather_sketch

ROOT = Path(__file__).resolve().parents[1]
CORE = Path("/home/claude/ard")                      # an Adafruit SAMD core checkout, present only in the sandbox that built this


def test_the_copies_in_the_sketch_folder_equal_the_originals():
    for name, src in feather_sketch.COPIES.items():
        assert (feather_sketch.SKETCH / name).read_text(encoding="utf-8") == src.read_text(encoding="utf-8"), name


def test_the_sketch_folder_and_sketch_file_have_the_same_name_as_the_arduino_ide_requires():
    assert (feather_sketch.SKETCH / (feather_sketch.SKETCH.name + ".ino")).is_file()


def test_the_sketch_times_the_same_three_functions_and_prints_the_same_log_lines_as_the_nano_app():
    ino = (feather_sketch.SKETCH / "timing_bench_feather.ino").read_text(encoding="utf-8")
    zeph = (ROOT / "bench" / "zephyr" / "src" / "main.c").read_text(encoding="utf-8")
    for name in ("cmp_naive", "cmp_ct", "cmp_memcmp"):
        entry = '"%s", %s' % (name, name)
        assert entry in ino and entry in zeph, name
    for key in ("ENV board ", "ENV cpu_hz_measured ", "ENV timer_overhead_min_cycles ", "ENV reps "):
        assert key in ino and key in zeph, key
    assert "#define REPEATS 1000u" in ino and "#define REPEATS 1000u" in zeph


@pytest.mark.skipif(not (CORE / "ArduinoCore-samd").is_dir() or shutil.which("arm-none-eabi-g++") is None, reason="needs the Adafruit SAMD core and an ARM compiler (sandbox only)")
def test_the_sketch_and_its_c_files_compile_against_the_adafruit_feather_m0_core(tmp_path):
    core = CORE / "ArduinoCore-samd"
    cmsis = CORE / "ArduinoModule-CMSIS" / "CMSIS"
    if not (cmsis / "Include" / "core_cm0plus.h").is_file():                       # the submodule is empty in this checkout: use the copy inside the bootloader sources
        cmsis = core / "bootloaders" / "mzero" / "Bootloader_D21" / "src" / "ASF" / "thirdparty" / "CMSIS"
    atmel = CORE / "ArduinoModule-CMSIS-Atmel" / "CMSIS-Atmel" / "CMSIS" / "Device" / "ATMEL"
    flags = ["-mcpu=cortex-m0plus", "-mthumb", "-Os", "-Wall", "-Wextra", "-DF_CPU=48000000L", "-DARDUINO=10819", "-DARDUINO_SAMD_FEATHER_M0", "-DARDUINO_ARCH_SAMD", "-D__SAMD21G18A__",
             "-DUSB_VID=0x239A", "-DUSB_PID=0x800B", "-DUSBCON", '-DUSB_MANUFACTURER="Adafruit"', '-DUSB_PRODUCT="Feather M0"',
             f"-I{core / 'cores' / 'arduino'}", f"-I{core / 'variants' / 'feather_m0'}", f"-I{cmsis / 'Include'}", f"-I{atmel}", f"-I{feather_sketch.SKETCH}"]
    for src, extra in (("timing_bench_feather.ino", ["-x", "c++", "-std=gnu++11", "-fno-rtti", "-fno-exceptions"]), ("timing_core.c", ["-std=gnu11"]), ("compare.c", ["-std=gnu11"])):
        r = subprocess.run(["arm-none-eabi-g++" if src.endswith(".ino") else "arm-none-eabi-gcc", *flags, *extra, "-c", str(feather_sketch.SKETCH / src), "-o", str(tmp_path / (src + ".o"))],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-1500:]
