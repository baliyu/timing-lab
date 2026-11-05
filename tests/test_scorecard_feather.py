"""The first Feather M0 capture (bench/logs/feather_run1.log) against docs/PREDICTIONS.md as it stood after revision 3, before the board was run.
Where a prediction missed, the test records the miss (and by how much), so the scorecard says what happened rather than what was hoped."""
from pathlib import Path

import pytest

from timing_lab import check

ROOT = Path(__file__).resolve().parents[1]
RUNS, ENV, IGNORED = check.parse((ROOT / "bench" / "logs" / "feather_run1.log").read_text(encoding="utf-8"))
RUN = RUNS[0]
ROWS = {(r["function"], r["n"]): r for r in check.analyse(RUN)}


def mean(fn, n, p):
    return RUN[(fn, n, p)].mean


def test_the_capture_is_usable_five_complete_runs_nothing_ignored_and_no_wrong_answers():
    assert len(RUNS) == 5 and IGNORED == 0
    assert all(x["errors"] == 0 for rr in (check.analyse(r) for r in RUNS) for x in rr)
    assert abs(int(ENV["cpu_hz_measured"]) - 48_000_000) < 48_000 and ENV["reps"] == "1000" and ENV["timer_overhead_min_cycles"] == "36"


@pytest.mark.parametrize("n", [4, 16, 32])
def test_p1_the_naive_loop_costs_12_to_20_cycles_per_matching_byte(n):
    assert 12.0 <= ROWS[("cmp_naive", n)]["slope"] <= 20.0 and ROWS[("cmp_naive", n)]["slope"] == pytest.approx(12.0)      # at the bottom of the range: no wait-state penalty seen


@pytest.mark.parametrize("n,total", [(4, 144), (16, 300), (32, 508)])
def test_p2_the_constant_time_loop_is_constant_within_2_cycles(n, total):
    assert ROWS[("cmp_ct", n)]["spread"] <= 2 and ROWS[("cmp_ct", n)]["spread"] == 0
    assert all(mean("cmp_ct", n, p) == total for p in range(n + 1))


def test_p2_the_constant_time_loop_costs_13_cycles_per_byte():
    assert (mean("cmp_ct", 32, 0) - mean("cmp_ct", 4, 0)) / 28 == 13.0


@pytest.mark.parametrize("n", [4, 16, 32])
def test_p3_the_memcmp_slope_is_inside_11_to_18_cycles_per_byte(n):
    assert 11.0 <= ROWS[("cmp_memcmp", n)]["slope"] <= 18.0


@pytest.mark.parametrize("n,predicted", [(4, 33), (16, 165), (32, 341)])
def test_p3_the_memcmp_spread_was_predicted_exactly_and_missed_by_one_cycle(n, predicted):
    assert ROWS[("cmp_memcmp", n)]["spread"] == pytest.approx(predicted + 1, abs=0.01)     # a miss: the first matching byte costs 12 cycles, not 11 (the means carry 0.001 from one low sample)


def test_p3_the_memcmp_cost_is_linear_with_no_staircase_except_that_the_first_step_is_one_cycle_longer():
    steps = [mean("cmp_memcmp", 16, p + 1) - mean("cmp_memcmp", 16, p) for p in range(15)]
    assert steps == pytest.approx([12.0] + [11.0] * 14, abs=0.01)


def test_p7_for_a_four_byte_tag_the_naive_loop_leaks_36_cycles_and_memcmp_34_where_33_was_predicted():
    naive = mean("cmp_naive", 4, 3) - mean("cmp_naive", 4, 0)
    mem = mean("cmp_memcmp", 4, 3) - mean("cmp_memcmp", 4, 0)
    assert naive == 36 and mem == 34
    assert naive / (int(ENV["cpu_hz_measured"]) / 1e6) == pytest.approx(0.75, abs=0.005)
    assert mem / (int(ENV["cpu_hz_measured"]) / 1e6) == pytest.approx(0.708, abs=0.005)


def test_p8_the_early_exit_functions_are_flagged_and_the_constant_time_one_is_not():
    for fn in ("cmp_naive", "cmp_memcmp"):
        assert all(ROWS[(fn, n)]["verdict"] == "leak" and abs(ROWS[(fn, n)]["t"]) > check.LEAK_T for n in (4, 16, 32))
    assert all(ROWS[("cmp_ct", n)]["verdict"] == "no difference seen" and ROWS[("cmp_ct", n)]["t"] == 0 for n in (4, 16, 32))


def test_the_only_variation_is_one_call_per_case_that_was_one_cycle_faster_in_the_two_early_exit_functions():
    varied = {k for k, s in RUN.items() if s.min != s.max}
    assert {k[0] for k in varied} == {"cmp_naive", "cmp_memcmp"} and len(varied) == 110
    assert all(RUN[k].max - RUN[k].min == 1 and RUN[k].max * RUN[k].reps - RUN[k].sum == 1 for k in varied)
    assert not any(s.min != s.max for k, s in RUN.items() if k[0] == "cmp_ct")
