"""Tests for timing_lab.align_compare on small synthetic logs. Built with AI assistance (Claude)."""
import sys

import pytest

from timing_lab import align_compare


def t(fn, n, p, reps, total):
    return "T,%s,%d,%d,%d,0,1,9,%d,0" % (fn, n, p, reps, total)


def run(k, memcmp_sum, ct_sum, end=True):
    lines = ["BEGIN run %d" % k,
             t("cmp_memcmp", 4, 0, 10, memcmp_sum),
             t("cmp_memcmp", 8, 0, 10, memcmp_sum),
             t("cmp_ct", 4, 0, 10, ct_sum)]
    if end:
        lines.append("END run %d" % k)
    return lines


@pytest.fixture
def logs(tmp_path):
    a = tmp_path / "a.log"
    b = tmp_path / "b.log"
    a.write_text("\n".join(["ENV x,1"] + run(0, 100, 200) + run(1, 120, 200)
                           + run(2, 99999, 99999, end=False)) + "\n")
    b.write_text("\n".join(run(0, 150, 190)) + "\n")
    return a, b


def test_means_counts_only_complete_runs(logs):
    m, complete = align_compare.means(logs[0])
    assert complete == 2
    assert m[("cmp_memcmp", 4, 0)] == pytest.approx(11.0)
    assert m[("cmp_ct", 4, 0)] == pytest.approx(20.0)


def test_partial_run_is_ignored(logs):
    m, _ = align_compare.means(logs[0])
    assert max(m.values()) < 1000


def test_mismatched_end_number_is_not_a_complete_run(tmp_path):
    p = tmp_path / "c.log"
    p.write_text("BEGIN run 0\n" + t("cmp_ct", 4, 0, 10, 100) + "\nEND run 1\n")
    m, complete = align_compare.means(p)
    assert complete == 0 and m == {}


def test_main_prints_difference(logs, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["align_compare", str(logs[0]), str(logs[1])])
    assert align_compare.main() == 0
    out = capsys.readouterr().out
    assert "complete runs: 2 and 1" in out
    mem = [l for l in out.splitlines() if l.startswith("cmp_memcmp")][0]
    assert "positions   2" in mem and "4.00 cycles at n=4 p=0" in mem and "+4.00" in mem
    ct = [l for l in out.splitlines() if l.startswith("cmp_ct")][0]
    assert "1.00 cycles" in ct and "-1.00" in ct


def test_main_writes_png(logs, monkeypatch, tmp_path, capsys):
    pytest.importorskip("matplotlib")
    png = tmp_path / "out.png"
    monkeypatch.setattr(sys, "argv", ["align_compare", str(logs[0]), str(logs[1]),
                                      "--labels", "ctl", "off1", "--png", str(png)])
    assert align_compare.main() == 0
    assert png.stat().st_size > 1000
    assert "saved" in capsys.readouterr().out
