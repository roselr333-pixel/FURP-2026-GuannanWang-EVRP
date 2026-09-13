"""
Paired significance tests for the collaborative-heuristic comparisons.

The reports so far quote mean improvements (e.g. "V2 is 42% shorter than V1")
but never test whether those differences are larger than the run-to-run noise.
This module runs a Wilcoxon signed-rank test on the *paired per-instance*
results (same instance, same seed, two methods) for every headline comparison:

  W7  my V2        vs  published (Murray & Chu 2015)   -- the improvement claim
  W7  my V2        vs  abl_cap1                        -- multi-customer effect
  W7  my V2        vs  abl_notakeoff                   -- multi-takeoff effect
  W8  LNS          vs  greedy V2                       -- improvement phase
  W6  V2           vs  V1                              -- collaborative vs EV

The Wilcoxon signed-rank test is implemented directly with numpy (rank of
|difference| with tie averaging, normal approximation with tie and continuity
correction, two-sided p).  No SciPy dependency is added, so the numbers stay
reproducible with the project's existing requirements.

Run:
  python src/experiments/stat_tests.py
"""

import os
import csv
import math
from collections import Counter

import numpy as np


def wilcoxon_signed_rank(a, b):
    """Two-sided Wilcoxon signed-rank test on paired samples a vs b.

    Returns a dict with n (nonzero pairs), mean/median of (a-b), W+, W-, z and
    the two-sided p-value (normal approximation, tie & continuity corrected)."""
    d = [x - y for x, y in zip(a, b)]
    d = [v for v in d if abs(v) > 1e-12]
    n = len(d)
    if n == 0:
        return None
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(abs(d[order[j + 1]]) - abs(d[order[i]])) < 1e-12:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    w_plus = sum(ranks[i] for i in range(n) if d[i] > 0)
    w_minus = sum(ranks[i] for i in range(n) if d[i] < 0)
    mu = n * (n + 1) / 4.0
    tie = sum(t ** 3 - t for t in Counter(round(abs(v), 9) for v in d).values())
    sigma2 = n * (n + 1) * (2 * n + 1) / 24.0 - tie / 48.0
    sigma = math.sqrt(sigma2) if sigma2 > 0 else 0.0
    if sigma > 0:
        z = (w_plus - mu - 0.5 * (1 if w_plus >= mu else -1)) / sigma
        p = math.erfc(abs(z) / math.sqrt(2))
    else:
        z, p = 0.0, 1.0
    return {
        "n_pairs": len(a),
        "n_nonzero": n,
        "mean_diff": float(np.mean(d)),
        "median_diff": float(np.median(d)),
        "w_plus": round(w_plus, 1),
        "w_minus": round(w_minus, 1),
        "z": round(z, 3),
        "p_value": p,
    }


def _read(path):
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _col(rows, name):
    return [float(r[name]) for r in rows]


def _test(a_rows, col_a, col_b, label, scope, out):
    try:
        a = _col(a_rows, col_a)
        b = _col(a_rows, col_b)
    except (KeyError, ValueError):
        return None
    r = wilcoxon_signed_rank(a, b)
    if r is None:
        return None
    row = {"comparison": label, "scope": scope, "col_a": col_a, "col_b": col_b}
    row.update(r)
    row["sig_0.05"] = "yes" if r["p_value"] < 0.05 else "no"
    out.append(row)
    return row


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    out_rows = []
    log = []

    def section(title):
        log.append("")
        log.append("=" * 78)
        log.append(title)
        log.append("=" * 78)

    # ---- W7 ablation: my V2 vs published / abl_cap1 / abl_notakeoff ----
    abl = _read(os.path.join(res, "week07_ablation_raw.csv"))
    if abl:
        section("W7 ablation (paired per instance; negative mean_diff = "
                "first method has smaller makespan)")
        for col_a, col_b, lab in [
                ("v2_mk", "published_mk", "my V2 vs published (M&C 2015)"),
                ("v2_mk", "abl_cap1_mk", "my V2 vs abl_cap1 (multi-customer)"),
                ("v2_mk", "abl_notakeoff_mk", "my V2 vs abl_notakeoff (multi-takeoff)")]:
            _test(abl, col_a, col_b, lab, "all sizes", out_rows)
            for n in sorted({r["size"] for r in abl}, key=lambda s: int(s)):
                sub = [r for r in abl if r["size"] == n]
                _test(sub, col_a, col_b, lab, f"N={n}", out_rows)
        for row in out_rows:
            log.append(
                f"  [{row['scope']:>8}] {row['comparison']:<42} "
                f"n={row['n_nonzero']:>3}  mean_diff={row['mean_diff']:8.2f}  "
                f"p={row['p_value']:.2e}  sig={row['sig_0.05']}")

    # ---- W8 LNS: LNS vs greedy V2 ----
    lns = _read(os.path.join(res, "week08_lns_raw.csv"))
    n_before = len(out_rows)
    if lns:
        section("W8 LNS (paired per instance)")
        _test(lns, "lns_mk", "greedy_mk", "LNS vs greedy V2", "all sizes", out_rows)
        for n in sorted({r["size"] for r in lns}, key=lambda s: int(s)):
            sub = [r for r in lns if r["size"] == n]
            _test(sub, "lns_mk", "greedy_mk", "LNS vs greedy V2", f"N={n}", out_rows)
        for row in out_rows[n_before:]:
            log.append(
                f"  [{row['scope']:>8}] {row['comparison']:<42} "
                f"n={row['n_nonzero']:>3}  mean_diff={row['mean_diff']:8.2f}  "
                f"p={row['p_value']:.2e}  sig={row['sig_0.05']}")

    # ---- W8 multi-drone: K drones vs 1 drone ----
    md = _read(os.path.join(res, "week08_multidrone_raw.csv"))
    n_before = len(out_rows)
    if md:
        section("W8 multi-drone (paired per instance; more drones vs 1)")
        for label, ca, cb in [
                ("LNS K=2 vs K=1", "K2_lns_mk", "K1_lns_mk"),
                ("LNS K=3 vs K=1", "K3_lns_mk", "K1_lns_mk"),
                ("greedy K=2 vs K=1", "K2_greedy_mk", "K1_greedy_mk"),
                ("greedy K=3 vs K=1", "K3_greedy_mk", "K1_greedy_mk")]:
            _test(md, ca, cb, label, "all sizes", out_rows)
            for n in sorted({r["size"] for r in md}, key=lambda s: int(s)):
                sub = [r for r in md if r["size"] == n]
                _test(sub, ca, cb, label, f"N={n}", out_rows)
        for row in out_rows[n_before:]:
            log.append(
                f"  [{row['scope']:>8}] {row['comparison']:<42} "
                f"n={row['n_nonzero']:>3}  mean_diff={row['mean_diff']:8.2f}  "
                f"p={row['p_value']:.2e}  sig={row['sig_0.05']}")

    # ---- W6 ground-air: V2 vs V1 ----
    ga = _read(os.path.join(res, "week06_ground_air_results.csv"))
    n_before = len(out_rows)
    if ga:
        section("W6 ground-air (paired per instance)")
        _test(ga, "V2_makespan", "V1_makespan", "V2 vs V1 (collaborative vs EV)",
              "all sizes", out_rows)
        for n in sorted({r["size"] for r in ga}, key=lambda s: int(s)):
            sub = [r for r in ga if r["size"] == n]
            _test(sub, "V2_makespan", "V1_makespan",
                  "V2 vs V1 (collaborative vs EV)", f"N={n}", out_rows)
        for row in out_rows[n_before:]:
            log.append(
                f"  [{row['scope']:>8}] {row['comparison']:<42} "
                f"n={row['n_nonzero']:>3}  mean_diff={row['mean_diff']:8.2f}  "
                f"p={row['p_value']:.2e}  sig={row['sig_0.05']}")

    out_csv = os.path.join(res, "stat_tests.csv")
    fields = ["comparison", "scope", "col_a", "col_b", "n_pairs", "n_nonzero",
              "mean_diff", "median_diff", "w_plus", "w_minus", "z", "p_value",
              "sig_0.05"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in out_rows:
            w.writerow({k: row.get(k, "") for k in fields})

    text = "\n".join(log)
    out_txt = os.path.join(res, "stat_tests_log.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[{len(out_rows)} tests -> {out_csv}]")


if __name__ == "__main__":
    main()
