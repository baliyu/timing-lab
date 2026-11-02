"""The portable bench core and the checker, end to end, with a fake cycle counter on the PC (this tests the logic; it measures nothing real)."""
import subprocess
from pathlib import Path

import pytest

from timing_lab import check

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exe(tmp_path_factory):
    out = tmp_path_factory.mktemp("host") / "host_fake"
    subprocess.run(["gcc", "-O1", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "bench" / "core"), "-I", str(ROOT / "c"),
                    str(ROOT / "bench" / "host" / "host_fake.c"), str(ROOT / "bench" / "core" / "timing_core.c"), str(ROOT / "c" / "compare.c"), "-o", str(out)], check=True)
    return out


def run(exe, mode):
    r = subprocess.run([str(exe), mode], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def lines(text):
    return [l for l in text.splitlines() if l.startswith("T,")]


def fields(l):
    f = l.split(",")
    return f[1], *[int(x) for x in f[2:]]


def test_one_pass_prints_every_function_length_and_position_between_begin_and_end(exe):
    rc, out, err = run(exe, "fixed")
    assert rc == 0 and "errors 0" in err
    ls = out.splitlines()
    assert ls[0] == "BEGIN run 1" and ls[-1] == "END run 1"
    assert len(lines(out)) == 3 * (5 + 17 + 33)                       # 3 functions; for n = 4, 16, 32 the positions 0..n


def test_with_a_fake_counter_that_always_advances_the_same_amount_every_statistic_is_exact(exe):
    _, out, _ = run(exe, "fixed")
    for l in lines(out):
        fn, n, p, reps, errors, vmin, vmax, vsum, vsumsq = fields(l)
        assert (reps, errors, vmin, vmax, vsum, vsumsq) == (50, 0, 8, 8, 400, 3200)     # each call: 7 + 1 for the second counter read


def test_every_position_of_the_first_difference_appears_once_per_function_and_length(exe):
    _, out, _ = run(exe, "fixed")
    seen = {(f, n, p) for f, n, p, *_ in map(fields, lines(out))}
    assert seen == {(f, n, p) for f in ("cmp_naive", "cmp_ct", "cmp_memcmp") for n in (4, 16, 32) for p in range(n + 1)}


def test_the_model_functions_give_the_cycle_counts_the_model_says(exe):
    rc, out, _ = run(exe, "model")
    assert rc == 0
    got = {(f, n, p): vmin for f, n, p, reps, errors, vmin, vmax, vsum, vsumsq in map(fields, lines(out))}
    assert got[("cmp_naive", 4, 0)] == 6 + 12 * 1 and got[("cmp_naive", 4, 3)] == 6 + 12 * 4 and got[("cmp_naive", 4, 4)] == 6 + 12 * 4
    assert got[("cmp_ct", 4, 0)] == got[("cmp_ct", 4, 3)] == got[("cmp_ct", 4, 4)] == 6 + 13 * 4
    assert got[("cmp_ct", 32, 7)] == 6 + 13 * 32


def test_the_checker_finds_the_leaky_model_leaky_and_the_constant_one_not(exe):
    _, out, _ = run(exe, "model")
    runs, env, ignored = check.parse(out)
    assert len(runs) == 1 and ignored == 0
    rows = {(r["function"], r["n"]): r for r in check.analyse(runs[0])}
    assert rows[("cmp_naive", 32)]["slope"] == pytest.approx(12.0) and rows[("cmp_naive", 32)]["verdict"] == "leak"
    assert rows[("cmp_ct", 32)]["slope"] == pytest.approx(0.0) and rows[("cmp_ct", 32)]["spread"] == 0 and rows[("cmp_ct", 32)]["verdict"] == "no difference seen"
    assert all(r["errors"] == 0 for r in rows.values())


def test_a_comparison_that_gives_wrong_answers_is_reported_by_the_core(tmp_path):
    src = tmp_path / "bad.c"
    src.write_text('#include <stdio.h>\n#include "timing_core.h"\nstatic uint32_t t; static uint32_t cy(void){return t++;} static unsigned lk(void){return 0;} static void ul(unsigned k){(void)k;}\n'
                   'static void em(const char*l){puts(l);} static int always_equal(const uint8_t*a,const uint8_t*b,uint8_t n){(void)a;(void)b;(void)n;return 1;}\n'
                   'int main(void){timing_platform_t p={cy,lk,ul,em}; timing_fn_t f[]={{"cmp_naive",always_equal}}; return timing_run(&p,f,1,5,1)?1:0;}\n')
    exe = tmp_path / "bad"
    subprocess.run(["gcc", "-I", str(ROOT / "bench" / "core"), str(src), str(ROOT / "bench" / "core" / "timing_core.c"), "-o", str(exe)], check=True)
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    assert r.returncode == 1
    runs, _, _ = check.parse(r.stdout)
    assert sum(x["errors"] for x in check.analyse(runs[0])) > 0
