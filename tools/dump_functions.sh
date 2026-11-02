#!/bin/sh
# Writes the machine code of the three comparisons (and the library memcmp they may call) out of a built firmware, into a listing the tests can read.
# Use the objdump from the SAME toolchain that built the firmware.   Usage:  sh tools/dump_functions.sh path/to/zephyr.elf asm/nano_zephyr.lst
set -e
elf="$1"; out="$2"
[ -f "$elf" ] || { echo "usage: $0 path/to/firmware.elf output.lst"; exit 1; }
od=${OBJDUMP:-}
[ -n "$od" ] || od=$(command -v arm-zephyr-eabi-objdump || ls "$HOME"/zephyr-sdk-*/arm-zephyr-eabi/bin/arm-zephyr-eabi-objdump 2>/dev/null | tail -1 || command -v arm-none-eabi-objdump)
[ -x "$od" ] || { echo "no objdump found: set OBJDUMP=/path/to/arm-...-objdump"; exit 1; }
rd=$(echo "$od" | sed 's/objdump$/readelf/')
{
  echo "# built by: $($rd -p .comment "$elf" 2>/dev/null | grep -i gcc | head -1 | sed 's/^ *\[ *[0-9a-f]*\] *//')"
  echo "# firmware: $(basename "$elf"), disassembled with $("$od" --version | head -1)"
  for sym in cmp_naive cmp_ct cmp_memcmp memcmp; do        # one symbol at a time: objdump keeps only the last --disassemble=
    "$od" -d --no-show-raw-insn --disassemble=$sym "$elf" | sed -n '/^[0-9a-f]* <.*>:$/,$p'
  done
} > "$out"
echo "wrote $out: $(grep -c '^[0-9a-f]* <' "$out") functions"
