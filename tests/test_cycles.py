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
