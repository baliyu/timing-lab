from pathlib import Path

import pytest

from timing_lab import cycles

ROOT = Path(__file__).resolve().parents[1]


def listing(name):
    return cycles.parse((ROOT / "asm" / name).read_text(encoding="utf-8"))


M0 = listing("compare_m0plus_Os.lst")
M4 = listing("compare_m4_O2.lst")


def test_the_listings_contain_the_three_functions():
    assert set(M0) == set(M4) == {"cmp_naive", "cmp_ct", "cmp_memcmp"}


def test_parse_reads_addresses_mnemonics_and_operands():
    f = cycles.parse("00000000 <f>:\n   0:\tmovs\tr3, #0\n   2:\tldrb.w\tr3, [r0], #1\n")["f"]
    assert [(i.addr, i.mnem, i.ops) for i in f] == [(0, "movs", "r3, #0"), (2, "ldrb.w", "r3, [r0], #1")]


@pytest.mark.parametrize("text,taken,cost", [("movs r3, #0", False, 1), ("ldrb r4, [r0, r3]", False, 2), ("str r1, [r0]", False, 2), ("beq.n 6 <f+0x6>", True, 2),
                                             ("beq.n 6 <f+0x6>", False, 1), ("b.n e <f+0xe>", False, 2), ("push {r4, r5, lr}", False, 4), ("adcs r0, r3", False, 1),
                                             ("bl 0 <memcmp>", False, 3)])
def test_cycle_costs_of_single_instructions_on_the_m0plus(text, taken, cost):
    mnem, _, ops = text.partition(" ")
    assert cycles.cost_m0plus(cycles.Insn(0, mnem, ops), taken) == cost


def test_a_matching_byte_costs_12_cycles_in_the_naive_loop_on_the_m0plus():
    # the loop from 0x6 to 0x18: uxtb, cmp, bhi (taken), ldrb, adds, ldrb, cmp, beq (taken, back to the top)
    assert cycles.path_cycles(M0["cmp_naive"], [0x6, 0x8, 0xA, 0x10, 0x12, 0x14, 0x16, 0x18], taken={0xA, 0x18}) == 12


def test_one_pass_of_the_constant_time_loop_costs_13_cycles_whatever_the_data():
    # uxtb, cmp, bhi (taken), ldrb, ldrb, adds, eors, orrs, b (back to the top)
    assert cycles.path_cycles(M0["cmp_ct"], [0x26, 0x28, 0x2A, 0x32, 0x34, 0x36, 0x38, 0x3A, 0x3C], taken={0x2A}) == 13


def test_the_naive_loop_has_a_branch_that_depends_on_the_data_on_both_cores():
    assert cycles.analyse(M0["cmp_naive"])[0] == [0x18]
    assert cycles.analyse(M4["cmp_naive"])[0] == [0x16]


def test_the_constant_time_loop_has_no_branch_that_depends_on_the_data_on_both_cores():
    assert cycles.analyse(M0["cmp_ct"])[0] == []
    assert cycles.analyse(M4["cmp_ct"])[0] == []


def test_the_memcmp_wrapper_has_no_data_branch_of_its_own_but_calls_memcmp_which_is_not_analysed():
    for lst in (M0, M4):
        flagged, calls = cycles.analyse(lst["cmp_memcmp"])
        assert flagged == [] and any("memcmp" in ops for _, ops in calls)


def test_loading_a_value_then_comparing_it_and_branching_is_reported():
    f = cycles.parse("00000000 <f>:\n   0:\tldrb\tr1, [r0, #0]\n   2:\tcmp\tr1, #7\n   4:\tbeq.n\t0 <f>\n")["f"]
    assert cycles.analyse(f)[0] == [4]


def test_comparing_only_a_counter_is_not_reported():
    f = cycles.parse("00000000 <f>:\n   0:\tldrb\tr1, [r0, #0]\n   2:\tadds\tr3, #1\n   4:\tcmp\tr3, r2\n   6:\tbne.n\t0 <f>\n")["f"]
    assert cycles.analyse(f)[0] == []


def test_an_immediate_move_clears_the_data_taint_of_a_register():
    f = cycles.parse("00000000 <f>:\n   0:\tldrb\tr1, [r0, #0]\n   2:\tmovs\tr1, #0\n   4:\tcmp\tr1, #7\n   6:\tbeq.n\t0 <f>\n")["f"]
    assert cycles.analyse(f)[0] == []


def test_data_flows_through_arithmetic_into_a_later_branch():
    f = cycles.parse("00000000 <f>:\n   0:\tldrb\tr1, [r0, #0]\n   2:\teors\tr2, r1\n   4:\tcmp\tr2, #0\n   6:\tbne.n\t0 <f>\n")["f"]
    assert cycles.analyse(f)[0] == [6]


def test_a_compare_and_branch_on_zero_of_loaded_data_is_reported():
    f = cycles.parse("00000000 <f>:\n   0:\tldrb\tr2, [r0, #0]\n   2:\tcbz\tr2, 8 <f+0x8>\n")["f"]
    assert cycles.analyse(f)[0] == [2]


def test_the_flags_set_by_an_arithmetic_instruction_count_too():
    f = cycles.parse("00000000 <f>:\n   0:\tldrb\tr1, [r0, #0]\n   2:\tsubs\tr1, #1\n   4:\tbne.n\t0 <f>\n")["f"]
    assert cycles.analyse(f)[0] == [4]


import re


def shape(func):
    """The instruction sequence without addresses or branch targets, ignoring padding nops."""
    return [(i.mnem, re.sub(r"[0-9a-f]+ <[^>]+>", "T", i.ops)) for i in func if i.mnem != "nop"]


NANO = listing("nano_sandbox_gcc13.lst")


def test_the_nano_firmware_build_contains_the_three_comparisons_and_the_memcmp_they_may_call():
    assert set(NANO) == {"cmp_naive", "cmp_ct", "cmp_memcmp", "memcmp"}


def test_the_comparisons_in_the_zephyr_build_are_the_same_loops_as_in_the_standalone_m4_listing():
    assert shape(NANO["cmp_naive"]) == shape(M4["cmp_naive"])
    assert shape(NANO["cmp_ct"]) == shape(M4["cmp_ct"])


def test_the_memcmp_linked_into_the_nano_build_is_a_byte_loop_with_an_early_exit():
    flagged, calls = cycles.analyse(NANO["memcmp"])
    assert flagged and calls == []
    assert sum(1 for i in NANO["memcmp"] if cycles.base(i.mnem) == "ldrb") >= 2          # it reads bytes, not words


def test_the_nano_wrapper_calls_the_library_memcmp():
    assert any("memcmp" in ops for _, ops in cycles.analyse(NANO["cmp_memcmp"])[1])


REAL = listing("nano_real.lst")


def test_the_listing_from_my_own_build_says_it_was_made_by_the_zephyr_sdk_compiler():
    head = (ROOT / "asm" / "nano_real.lst").read_text(encoding="utf-8").splitlines()[:2]
    assert "Zephyr SDK 1.0.1" in head[0] and "14.3.0" in head[0]


def test_the_three_comparisons_in_my_own_build_are_the_same_loops_as_in_the_sandbox_build():
    for name in ("cmp_naive", "cmp_ct", "cmp_memcmp"):
        assert shape(REAL[name]) == shape(NANO[name]), name


def test_in_my_own_build_the_naive_loop_has_a_data_branch_and_the_constant_time_loop_has_none():
    assert cycles.analyse(REAL["cmp_naive"])[0] and cycles.analyse(REAL["cmp_ct"])[0] == []


def test_the_memcmp_in_my_own_build_compares_words_when_both_pointers_are_aligned_and_falls_back_to_bytes():
    m = REAL["memcmp"]
    ops = [(i.mnem, i.ops) for i in m]
    assert any(mn.startswith("ldr.w") and ", #4" in o for mn, o in ops)                 # a post-incremented word load: 4 bytes at a time
    assert any(mn == "lsls" and "#30" in o for mn, o in ops)                             # the test of the low two address bits of both pointers
    assert sum(1 for mn, _ in ops if mn.startswith("ldrb")) >= 2                         # and the byte loop
    assert len(cycles.analyse(m)[0]) >= 2                                                # several branches that depend on the data


def test_the_memcmp_in_the_two_builds_is_not_the_same_code():
    assert shape(REAL["memcmp"]) != shape(NANO["memcmp"])
