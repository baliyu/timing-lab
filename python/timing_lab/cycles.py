"""Static reading of Thumb code from an objdump listing: cycles along a path (Cortex-M0+ costs) and a check for branches that depend on loaded data.

This is a reading aid, not a proof.  Cycle costs assume zero wait states (the Cortex-M0 manual's table is stated that way) so a real board with flash
wait states will be slower.  The data-dependence check is a simple one-pass taint walk in address order: any value loaded from memory is 'data', and a conditional
branch is reported when the flags it uses were set from data.  It is meant for short functions like these; read what it reports."""
from __future__ import annotations

import re
from collections import namedtuple

Insn = namedtuple("Insn", "addr mnem ops")

_FUNC = re.compile(r"^[0-9a-f]+ <([^>]+)>:")
_LINE = re.compile(r"^\s*([0-9a-f]+):\s+([a-z][a-z0-9.]*)\s*(.*?)\s*(?:;.*)?$")
_REG = re.compile(r"\b(r\d+|ip|lr|sp|pc|fp|sl|sb)\b")

COND = {"eq", "ne", "cs", "hs", "cc", "lo", "mi", "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le"}
LOADS = {"ldr", "ldrb", "ldrh", "ldrsb", "ldrsh"}
STORES = {"str", "strb", "strh"}
TWO_OP = {"adds", "subs", "eors", "orrs", "ands", "adcs", "sbcs", "bics", "muls", "lsls", "lsrs", "asrs", "rors",
          "add", "sub", "eor", "orr", "and", "adc", "sbc", "bic", "mul", "lsl", "lsr", "asr", "ror"}
FLAG_SETTERS = {"adds", "subs", "eors", "orrs", "ands", "adcs", "sbcs", "bics", "muls", "lsls", "lsrs", "asrs", "rors", "movs", "mvns", "negs", "rsbs"}


def parse(text):
    """{function name: [Insn, ...]} from `objdump -d --no-show-raw-insn` text."""
    funcs, cur = {}, None
    for line in text.splitlines():
        m = _FUNC.match(line)
        if m:
            cur = m.group(1)
            funcs[cur] = []
            continue
        m = _LINE.match(line)
        if m and cur is not None:
            funcs[cur].append(Insn(int(m.group(1), 16), m.group(2), m.group(3)))
    return funcs


def base(mnem):
    return mnem.split(".")[0]


def is_cond_branch(b):
    return b.startswith("b") and b[1:] in COND


def regs(ops):
    return _REG.findall(ops)


def cost_m0plus(ins, taken=False):
    """Cycles for one instruction on a Cortex-M0+ with zero wait states: loads and stores 2, taken branches 2 (not taken 1), push and pop 1 + registers, everything else 1."""
    b = base(ins.mnem)
    if b in LOADS or b in STORES:
        return 2
    if b in ("push", "pop"):
        return 1 + ins.ops.count(",") + 1
    if is_cond_branch(b):
        return 2 if taken else 1
    if b in ("b", "bx"):
        return 2
    if b in ("bl", "blx"):
        return 3
    return 1


def path_cycles(func, path, taken=()):
    """Sum of cycles for the instructions at the addresses in `path`, in order; `taken` holds the addresses of branches that are taken."""
    by_addr = {i.addr: i for i in func}
    return sum(cost_m0plus(by_addr[a], a in taken) for a in path)


def analyse(func):
    """(addresses of conditional branches that depend on loaded data, [(address, target text)] of calls that were not analysed)."""
    tainted, flags_tainted = set(), False
    flagged, calls = [], []
    for ins in func:
        b = base(ins.mnem)
        r = regs(ins.ops)
        if b in LOADS:
            if r:
                tainted.add(r[0])
        elif b in ("cmp", "cmn", "tst", "teq"):
            flags_tainted = any(x in tainted for x in r)
        elif is_cond_branch(b):
            if flags_tainted:
                flagged.append(ins.addr)
        elif b in ("cbz", "cbnz"):
            if r and r[0] in tainted:
                flagged.append(ins.addr)
        elif b in ("bl", "blx"):
            calls.append((ins.addr, ins.ops))
        elif b in ("b", "bx", "nop", "push", "pop") or b in STORES:
            continue
        elif r:
            dest = r[0]
            if len(r) >= 3:
                srcs = r[1:]
            elif len(r) == 2:
                srcs = r if b in TWO_OP else r[1:]
            else:
                srcs = r if b in TWO_OP else []
            is_data = any(x in tainted for x in srcs)
            (tainted.add if is_data else tainted.discard)(dest)
            if b in FLAG_SETTERS:
                flags_tainted = is_data
    return flagged, calls
