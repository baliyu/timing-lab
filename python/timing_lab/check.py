"""Reads a bench log (lines T,function,n,p,reps,errors,min,max,sum,sumsq between BEGIN run k and END run k) and says, for each function and length, how the cycle count
depends on the position p of the first difference: the slope in cycles per matching byte, the spread across positions, and a Welch t between "the first byte differs" (p = 0)
and "only the last byte differs" (p = n - 1).  |t| above 4.5 is the usual threshold for calling a timing difference a leak.  A difference that is statistically clear is not
necessarily one an attacker could use: that depends on what else adds noise between the attacker and the comparison.

python -m timing_lab.check LOGFILE [--json]    (exit 0 = log read; 1 = unusable log; 2 = a comparison gave a wrong answer in some run)"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

LEAK_T = 4.5
_T = re.compile(r"^T,(\w+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$")
_BEGIN = re.compile(r"^BEGIN run (\d+)$")
_END = re.compile(r"^END run (\d+)$")
_ENV = re.compile(r"^ENV (\S+) (.*)$")


class Stats:
    def __init__(self, reps, errors, vmin, vmax, vsum, vsumsq):
        self.reps, self.errors, self.min, self.max, self.sum, self.sumsq = reps, errors, vmin, vmax, vsum, vsumsq

    @property
    def mean(self):
        return self.sum / self.reps

    @property
    def var(self):
        if self.reps < 2:
            return 0.0
        return max(0.0, (self.sumsq - self.sum * self.sum / self.reps) / (self.reps - 1))


def parse(text):
    """(complete runs as a list of {(function, n, p): Stats}, the ENV lines as a dict, the number of lines ignored)."""
    runs, env, ignored = [], {}, 0
    cur, cur_id = None, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _BEGIN.match(line)
        if m:
            cur, cur_id = {}, m.group(1)
            continue
        m = _END.match(line)
        if m:
            if cur is not None and m.group(1) == cur_id and cur:
                runs.append(cur)
            else:
                ignored += 1
            cur = None
            continue
        m = _ENV.match(line)
        if m:
            env[m.group(1)] = m.group(2)
            continue
        m = _T.match(line)
        if m and cur is not None:
            fn, n, p, reps, errors, vmin, vmax, vsum, vsumsq = m.groups()
            cur[(fn, int(n), int(p))] = Stats(int(reps), int(errors), int(vmin), int(vmax), int(vsum), int(vsumsq))
            continue
        ignored += 1                                  # a partial run at the start, a damaged line, or anything else
    return runs, env, ignored


def welch_t(a, b):
    """Welch's t for two summaries (inf when the means differ and neither class varies, 0 when they are identical)."""
    denom = math.sqrt(a.var / a.reps + b.var / b.reps)
    diff = a.mean - b.mean
    if denom == 0:
        return 0.0 if diff == 0 else math.copysign(math.inf, diff)
    return diff / denom


def slope(points):
    """Least-squares slope of y against x for [(x, y), ...]."""
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    sxx = sum((x - mx) ** 2 for x, _ in points)
    return sum((x - mx) * (y - my) for x, y in points) / sxx if sxx else 0.0


def analyse(run):
    """One row per (function, n): slope, spread of the mean over p < n, the mean when equal, t (first vs last byte), the verdict, and any wrong answers."""
    rows = []
    keys = sorted({(fn, n) for fn, n, _ in run}, key=lambda k: (k[0], k[1]))
    for fn, n in keys:
        pts = [(p, run[(fn, n, p)]) for p in range(n) if (fn, n, p) in run]
        if len(pts) != n or (fn, n, n) not in run:
            continue
        means = [s.mean for _, s in pts]
        t = welch_t(pts[0][1], pts[-1][1])
        errors = sum(s.errors for _, s in pts) + run[(fn, n, n)].errors
        rows.append({"function": fn, "n": n, "slope": slope([(p, s.mean) for p, s in pts]), "spread": max(means) - min(means),
                     "first_byte_mean": means[0], "last_byte_mean": means[-1], "equal_mean": run[(fn, n, n)].mean,
                     "t": t, "verdict": "leak" if abs(t) > LEAK_T else "no difference seen", "errors": errors})
    return rows


def fmt_t(t):
    return "inf" if math.isinf(t) else f"{t:.1f}"


def report(runs, env, ignored):
    rows = [analyse(r) for r in runs]
    first = rows[0]
    lines = [f"{len(runs)} complete run(s), {ignored} line(s) ignored"] + [f"  {k} = {v}" for k, v in env.items() if k in ("board", "zephyr", "cpu_hz_measured", "timer_overhead_min_cycles", "reps", "mcu", "core")]
    lines.append("  function      n   slope(cyc/byte)  spread(cyc)  first-byte mean  last-byte mean     t   verdict")
    for r in first:
        lines.append(f"  {r['function']:11s} {r['n']:3d}   {r['slope']:15.2f}  {r['spread']:11.2f}  {r['first_byte_mean']:15.2f}  {r['last_byte_mean']:14.2f}  {fmt_t(r['t']):>4s}   {r['verdict']}")
    agree = all([x["verdict"] for x in rows[0]] == [x["verdict"] for x in other] for other in rows[1:])
    lines.append(f"verdicts agree across runs: {'yes' if agree else 'NO'}")
    wrong = sum(x["errors"] for rr in rows for x in rr)
    if wrong:
        lines.append(f"INVALID: {wrong} call(s) gave a wrong answer, so the timings are not trustworthy")
    return "\n".join(lines), rows, wrong


def main(argv=None):
    ap = argparse.ArgumentParser(prog="timing_lab.check", description=__doc__.split("\n\n")[0])
    ap.add_argument("log", help="the bench log file")
    ap.add_argument("--json", action="store_true", help="print the analysis of the first complete run as JSON instead of the table")
    args = ap.parse_args(argv)
    path = Path(args.log)
    if not path.is_file():
        print(f"no such file: {path}")
        return 1
    runs, env, ignored = parse(path.read_text(encoding="utf-8", errors="replace"))
    if not runs:
        print("no complete run in the log")
        return 1
    text, rows, wrong = report(runs, env, ignored)
    if args.json:
        print(json.dumps(rows[0], indent=1))
    else:
        print(text)
    return 2 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
