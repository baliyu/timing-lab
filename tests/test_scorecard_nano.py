"""The first Nano 33 BLE capture (bench/logs/nano_run1.log) against the ranges in docs/PREDICTIONS.md.  Each range below is copied from that file as it stood
before the board was run (revision 2), so these tests are the scorecard in executable form."""
from pathlib import Path

import pytest

from timing_lab import check

ROOT = Path(__file__).resolve().parents[1]
RUNS, ENV, IGNORED = check.parse((ROOT / "bench" / "logs" / "nano_run1.log").read_text(encoding="utf-8"))
RUN = RUNS[0]
ROWS = {(r["function"], r["n"]): r for r in check.analyse(RUN)}


def mean(fn, n, p):
    return RUN[(fn, n, p)].mean


def test_the_capture_is_usable_five_complete_runs_nothing_ignored_and_no_wrong_answers():
    assert len(RUNS) == 5 and IGNORED == 0
    assert all(x["errors"] == 0 for rr in (check.analyse(r) for r in RUNS) for x in rr)
    assert 63.5e6 < int(ENV["cpu_hz_measured"]) < 64.5e6 and ENV["reps"] == "1000"


def test_every_case_is_perfectly_repeatable_inside_a_run_and_identical_across_runs():
    for run in RUNS:
        assert all(s.min == s.max for s in run.values())
    for run in RUNS[1:]:
        assert all((s.min, s.sum, s.sumsq) == (RUN[k].min, RUN[k].sum, RUN[k].sumsq) for k, s in run.items())


@pytest.mark.parametrize("n", [4, 16, 32])
def test_p4_the_naive_loop_costs_8_to_11_cycles_per_matching_byte(n):
    assert 8.0 <= ROWS[("cmp_naive", n)]["slope"] <= 11.0


@pytest.mark.parametrize("n,total", [(4, 86), (16, 182), (32, 310)])
def test_p5_the_constant_time_loop_is_constant_within_3_cycles(n, total):
    assert ROWS[("cmp_ct", n)]["spread"] <= 3 and ROWS[("cmp_ct", n)]["spread"] == 0
    assert all(mean("cmp_ct", n, p) == total for p in range(n + 1))                 # the same count whether the strings are equal or differ anywhere


def test_the_constant_time_loop_costs_8_cycles_per_byte_here_the_same_as_a_matching_byte_of_the_naive_loop():
    assert (mean("cmp_ct", 32, 0) - mean("cmp_ct", 4, 0)) / 28 == 8.0


@pytest.mark.parametrize("n,slope_range,spread_range", [(4, (7.0, 10.0), (21, 30)), (16, (3.0, 3.9), (54, 72)), (32, (2.8, 3.6), (98, 128))])
def test_p6_the_memcmp_slope_and_spread_are_inside_the_predicted_ranges(n, slope_range, spread_range):
    r = ROWS[("cmp_memcmp", n)]
    assert slope_range[0] <= r["slope"] <= slope_range[1]
    assert spread_range[0] <= r["spread"] <= spread_range[1]


def test_p6_the_memcmp_cost_rises_in_steps_of_11_to_14_cycles_per_four_bytes():
    steps = {mean("cmp_memcmp", 32, p + 4) - mean("cmp_memcmp", 32, p) for p in range(28)}
    assert steps == {11.0}                                                          # inside 11 to 14, at its lower end: the model's 12 per word was one cycle high
    assert [mean("cmp_memcmp", 32, p + 1) - mean("cmp_memcmp", 32, p) for p in range(3)] == [8.0, 8.0, 8.0]      # and 8 per byte inside the word, as modelled


def test_p7_for_a_four_byte_tag_the_naive_loop_leaks_21_to_30_cycles_between_first_and_last_byte():
    d = mean("cmp_naive", 4, 3) - mean("cmp_naive", 4, 0)
    assert 21 <= d <= 30 and d == 24
    assert d / (int(ENV["cpu_hz_measured"]) / 1e6) == pytest.approx(0.375, abs=0.005)       # microseconds


def test_p8_the_early_exit_functions_are_flagged_and_the_constant_time_one_is_not():
    for fn in ("cmp_naive", "cmp_memcmp"):
        assert all(ROWS[(fn, n)]["verdict"] == "leak" and abs(ROWS[(fn, n)]["t"]) > check.LEAK_T for n in (4, 16, 32))
    assert all(ROWS[("cmp_ct", n)]["verdict"] == "no difference seen" and ROWS[("cmp_ct", n)]["t"] == 0 for n in (4, 16, 32))
