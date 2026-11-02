#!/bin/sh
# Rebuilds asm/*.lst from c/compare.c with the flags the boards' builds use: -Os for the Feather M0 (Cortex-M0+), -O2 for the Nano 33 BLE (Cortex-M4).
set -e
cd "$(dirname "$0")/.."
ver=$(arm-none-eabi-gcc --version | head -1)
one() {  # cpu opt outfile
  { echo "# $ver"; echo "# arm-none-eabi-gcc -mcpu=$1 -mthumb -$2 -c c/compare.c, then arm-none-eabi-objdump -d --no-show-raw-insn"
    arm-none-eabi-gcc -mcpu=$1 -mthumb -$2 -c c/compare.c -o /tmp/compare_$1.o
    arm-none-eabi-objdump -d --no-show-raw-insn /tmp/compare_$1.o | tail -n +4; } > "$3"
}
one cortex-m0plus Os asm/compare_m0plus_Os.lst
one cortex-m4 O2 asm/compare_m4_O2.lst
echo "wrote asm/compare_m0plus_Os.lst and asm/compare_m4_O2.lst"
