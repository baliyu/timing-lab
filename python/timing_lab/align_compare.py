"""Compares two bench logs position by position and, with --png, draws the library memcmp from both.

    PYTHONPATH=python python -m timing_lab.align_compare LOG_A LOG_B [--labels A B] [--title T] [--png OUT.png]

Only complete runs (BEGIN run k ... END run k) are used. Built with AI assistance (Claude)."""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

BEGIN = re.compile(r"^BEGIN run (\d+)$")
END = re.compile(r"^END run (\d+)$")


def means(path):
    """Mean cycles per (function, n, p) over the complete runs of one log, and the number of complete runs."""
    sums = defaultdict(lambda: [0, 0])
    run, rows, complete = None, [], 0
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        m = BEGIN.match(line)
        if m:
            run, rows = m.group(1), []
            continue
        m = END.match(line)
        if m and run == m.group(1):
            for key, s, reps in rows:
                sums[key][0] += s
                sums[key][1] += reps
            complete += 1
            run, rows = None, []
            continue
        if run is not None and line.startswith("T,"):
            f = line.split(",")
            if len(f) == 10:
                rows.append(((f[1], int(f[2]), int(f[3])), int(f[8]), int(f[4])))
    return {k: s / r for k, (s, r) in sums.items()}, complete


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--labels", nargs=2, default=["A", "B"])
    ap.add_argument("--title", default="")
    ap.add_argument("--png")
    args = ap.parse_args()
    ma, ca = means(args.a)
    mb, cb = means(args.b)
    print("complete runs: %d and %d" % (ca, cb))
    keys = sorted(set(ma) & set(mb))
    assert keys, "no positions in common"
    for fn in sorted({k[0] for k in keys}):
        d = [(mb[k] - ma[k], k) for k in keys if k[0] == fn]
        worst = max(d, key=lambda x: abs(x[0]))
        print("%-11s positions %3d  largest |B - A| %6.2f cycles at n=%d p=%d   mean B - A %+7.2f"
              % (fn, len(d), abs(worst[0]), worst[1][1], worst[1][2], sum(x[0] for x in d) / len(d)))
    if args.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ns = sorted({k[1] for k in keys if k[0] == "cmp_memcmp"})
        fig, axs = plt.subplots(1, len(ns), figsize=(4 * len(ns), 3.8))
        for ax, n in zip(axs, ns):
            ps = sorted(k[2] for k in keys if k[0] == "cmp_memcmp" and k[1] == n)
            ax.plot(ps, [ma[("cmp_memcmp", n, p)] for p in ps], "o-", ms=3, label=args.labels[0])
            ax.plot(ps, [mb[("cmp_memcmp", n, p)] for p in ps], "s--", ms=3, label=args.labels[1])
            ax.set_title("n = %d" % n)
            ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
            ax.set_xlabel("position of first difference (p = n: equal)")
        axs[0].set_ylabel("mean cycles per call")
        axs[0].legend(fontsize=8)
        fig.suptitle(args.title)
        fig.tight_layout()
        fig.savefig(args.png, dpi=150)
        print("saved", args.png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
