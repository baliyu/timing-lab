import math
import random

import pytest

from timing_lab import check


def stats_line(fn, n, p, samples, errors=0):
    return f"T,{fn},{n},{p},{len(samples)},{errors},{min(samples)},{max(samples)},{sum(samples)},{sum(s * s for s in samples)}"


def make_log(model, runs=1, reps=200, seed=1, noise=0, drop_end=False, junk=False):
    """model(fn, n, p) -> base cycles; noise: a random integer 0..noise added to each sample."""
    rnd = random.Random(seed)
    out = ["ENV board test", "ENV reps %d" % reps]
    for k in range(1, runs + 1):
        out.append(f"BEGIN run {k}")
        for fn in ("cmp_naive", "cmp_ct"):
            for n in (4, 16, 32):
                for p in range(n + 1):
                    base = model(fn, n, p)
                    out.append(stats_line(fn, n, p, [base + (rnd.randint(0, noise) if noise else 0) for _ in range(reps)]))
        if junk:
            out.append("T,cmp_ct,4,xx")
        if not (drop_end and k == runs):
            out.append(f"END run {k}")
    return "\n".join(out) + "\n"


LEAKY = lambda fn, n, p: (10 + 12 * (min(p, n - 1) + 1)) if fn == "cmp_naive" else 10 + 13 * n
FLAT = lambda fn, n, p: 10 + 13 * n


def rows(log):
    runs, env, ign = check.parse(log)
    return {(r["function"], r["n"]): r for r in check.analyse(runs[0])}


def test_a_leaky_function_shows_its_slope_and_a_large_t_even_with_noise():
    r = rows(make_log(LEAKY, noise=3))
    assert r[("cmp_naive", 16)]["slope"] == pytest.approx(12.0, abs=0.05)
    assert r[("cmp_naive", 16)]["verdict"] == "leak" and abs(r[("cmp_naive", 16)]["t"]) > 50
    assert r[("cmp_ct", 16)]["verdict"] == "no difference seen" and abs(r[("cmp_ct", 16)]["slope"]) < 0.05


def test_pure_noise_between_the_classes_is_not_called_a_leak():
    r = rows(make_log(FLAT, noise=5, seed=3))
    assert all(x["verdict"] == "no difference seen" and abs(x["t"]) < check.LEAK_T for x in r.values())


def test_welch_t_matches_the_textbook_formula_on_raw_samples():
    rnd = random.Random(7)
    a = [100 + rnd.randint(0, 9) for _ in range(300)]
    b = [102 + rnd.randint(0, 9) for _ in range(250)]
    sa = check.Stats(len(a), 0, min(a), max(a), sum(a), sum(x * x for x in a))
    sb = check.Stats(len(b), 0, min(b), max(b), sum(b), sum(x * x for x in b))
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    assert check.welch_t(sa, sb) == pytest.approx((ma - mb) / math.sqrt(va / len(a) + vb / len(b)), rel=1e-9)


def test_identical_classes_with_no_variance_give_t_zero_and_different_ones_give_infinity():
    same = check.Stats(10, 0, 5, 5, 50, 250)
    other = check.Stats(10, 0, 6, 6, 60, 360)
    assert check.welch_t(same, same) == 0.0 and math.isinf(check.welch_t(same, other)) and check.welch_t(same, other) < 0


def test_slope_of_a_straight_line_and_of_a_flat_one():
    assert check.slope([(0, 5), (1, 17), (2, 29), (3, 41)]) == pytest.approx(12.0)
    assert check.slope([(0, 9), (1, 9), (2, 9)]) == 0.0


def test_a_run_without_an_end_line_and_damaged_lines_are_ignored_and_counted():
    log = make_log(LEAKY, runs=2, drop_end=True, junk=True)
    runs, env, ignored = check.parse(log)
    assert len(runs) == 1 and ignored >= 1 and env["board"] == "test"
    runs, _, ignored = check.parse("T,cmp_ct,4,0,10,0,5,5,50,250\nBEGIN run 1\nEND run 1\n")
    assert runs == [] and ignored >= 1


def test_the_text_before_the_first_begin_is_ignored_and_a_log_with_two_runs_has_two_results():
    log = "garbled tail of a line\n" + make_log(FLAT, runs=2)
    runs, _, ignored = check.parse(log)
    assert len(runs) == 2 and ignored == 1


def test_the_report_says_whether_runs_agree_and_flags_wrong_answers():
    runs, env, ign = check.parse(make_log(LEAKY, runs=2))
    text, rr, wrong = check.report(runs, env, ign)
    assert "verdicts agree across runs: yes" in text and wrong == 0
    bad = make_log(FLAT).replace("T,cmp_ct,4,0,200,0,", "T,cmp_ct,4,0,200,3,")
    runs, env, ign = check.parse(bad)
    text, rr, wrong = check.report(runs, env, ign)
    assert wrong == 3 and "INVALID" in text


def test_command_line_exit_codes(tmp_path, capsys):
    f = tmp_path / "log.txt"
    f.write_text(make_log(LEAKY), encoding="utf-8")
    assert check.main([str(f)]) == 0
    assert "cmp_naive" in capsys.readouterr().out
    assert check.main([str(tmp_path / "missing.txt")]) == 1
    f.write_text("nothing useful\n", encoding="utf-8")
    assert check.main([str(f)]) == 1
    f.write_text(make_log(FLAT).replace("T,cmp_ct,4,0,200,0,", "T,cmp_ct,4,0,200,1,"), encoding="utf-8")
    assert check.main([str(f)]) == 2


def test_the_leak_threshold_is_4_5():
    def pair(delta):                                     # two classes of 100 samples with variance 1, means delta apart
        a = check.Stats(100, 0, 0, 0, 10000, 10000 * 100 + 99)
        b = check.Stats(100, 0, 0, 0, 10000 + int(delta * 100), 0)
        b.sumsq = int(b.sum * b.sum / 100 + 99)
        return a, b
    a, b = pair(0.5)
    assert abs(check.welch_t(a, b)) == pytest.approx(0.5 / math.sqrt(2 / 100), rel=1e-6) and abs(check.welch_t(a, b)) < check.LEAK_T
    a, b = pair(0.7)
    assert abs(check.welch_t(a, b)) > check.LEAK_T


def test_an_end_line_with_a_different_run_number_does_not_close_the_run():
    log = "BEGIN run 1\nT,cmp_ct,4,0,10,0,5,5,50,250\nEND run 2\n"
    runs, _, ignored = check.parse(log)
    assert runs == [] and ignored >= 1


def test_a_function_and_length_with_missing_positions_is_skipped_not_a_crash():
    log = make_log(FLAT).replace("T,cmp_naive,4,2,", "X,cmp_naive,4,2,")
    r = rows(log)
    assert ("cmp_naive", 4) not in r and ("cmp_naive", 16) in r


def test_wrong_answers_in_the_no_difference_case_are_counted_too():
    log = make_log(FLAT).replace("T,cmp_ct,4,4,200,0,", "T,cmp_ct,4,4,200,5,")
    assert rows(log)[("cmp_ct", 4)]["errors"] == 5
