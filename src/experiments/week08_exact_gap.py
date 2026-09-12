"""
Exact optimality gap on small instances (CP-SAT).

The project pages kept noting that "how far the heuristic is from the optimum is
not quantified". This runner quantifies it on small instances: for each instance
it computes

  * the EXACT optimum of the physical FSTSP model (cpsat_fstsp.solve_exact),
  * my V2 greedy restricted to that model (cpsat_fstsp.clean_greedy),
  * the LNS run on that model (week08_lns.lns with the physical evaluator),

and reports the gap of each heuristic to the optimum. It also re-evaluates the
project's V2 / LNS plans with the physical evaluator and records whether the
sortie sets are valid, so that the reported gap compares like with like (the
shared evaluator enforces the same physical rules).

Proven-optimal runs are flagged; where CP-SAT hits the time limit the returned
value is an upper bound on the optimum, so the reported gap is then a lower
bound on the true gap (stated in the log).

Run:
  python src/experiments/week08_exact_gap.py
"""

import os
import sys
import csv
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab
import week08_lns as L
import cpsat_fstsp as X
import sysinfo as SI

SIZES = [8, 10, 12]
N_SEEDS = 5
SEED_BASE = 20260720
MAX_CUST = 2
TIME_LIMIT = 180.0


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    os.makedirs(res, exist_ok=True)
    out_raw = os.path.join(res, "week08_exact_gap_raw.csv")
    out_sum = os.path.join(res, "week08_exact_gap_summary.csv")
    out_txt = os.path.join(res, "week08_exact_gap_log.txt")

    helper = lambda i, r, t: X.fstsp_makespan_clean(i, r, t)
    rows = []
    for n in SIZES:
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)

            # original project heuristics (shared evaluator) + validity of the
            # plan they produce
            r2, t2, _ = ab.my_v2_param(inst, max_cust=2, multi_takeoff=True)
            v2_raw = f7.fstsp_makespan(inst, r2, t2)
            v2_raw_valid = X.clean_simulate(inst, r2, t2)[0]

            # physical model: clean greedy + LNS
            gr, gt, _ = X.clean_greedy(inst, max_cust=MAX_CUST)
            mk_greedy = X.fstsp_makespan_clean(inst, gr, gt)
            lr, lt, mk_lns, _ = L.lns(
                inst, n, seed=seed, max_cust=MAX_CUST, eval_fn=helper,
                greedy_fn=lambda i: X.clean_greedy(i, max_cust=MAX_CUST))
            mk_lns = X.fstsp_makespan_clean(inst, lr, lt)

            res_ex = X.solve_exact(inst, max_cust=MAX_CUST,
                                   time_limit=TIME_LIMIT, num_workers=8)
            opt = res_ex["makespan"]
            row = {
                "size": n, "seed": seed,
                "opt": (round(opt, 2) if opt is not None else ""),
                "opt_proven": "yes" if res_ex["proven"] else "no",
                "opt_status": res_ex["status"],
                "opt_wall_s": res_ex["wall_s"],
                "greedy_mk": round(mk_greedy, 2),
                "lns_mk": round(mk_lns, 2),
                "greedy_gap_pct": (round((mk_greedy - opt) / opt * 100, 2)
                                   if opt else ""),
                "lns_gap_pct": (round((mk_lns - opt) / opt * 100, 2)
                                if opt else ""),
                "v2_raw_mk": round(v2_raw, 2),
                "v2_raw_plan_valid": "yes" if v2_raw_valid else "no",
            }
            rows.append(row)
            print(f"n={n} seed={seed}: OPT={row['opt']} "
                  f"({row['opt_status']}, {row['opt_wall_s']}s) | "
                  f"greedy {row['greedy_gap_pct']}% "
                  f"LNS {row['lns_gap_pct']}% | "
                  f"raw V2 valid={row['v2_raw_plan_valid']}", flush=True)

    summary = []
    for n in SIZES:
        sub = [r for r in rows if r["size"] == n]
        proven = [r for r in sub if r["opt_proven"] == "yes"]
        valid_raw = [r for r in sub if r["v2_raw_plan_valid"] == "yes"]
        summary.append({
            "size": n, "n_instances": len(sub),
            "n_opt_proven": len(proven),
            "greedy_gap_mean_pct": round(
                _mean([r["greedy_gap_pct"] for r in sub
                       if r["greedy_gap_pct"] != ""]), 2),
            "lns_gap_mean_pct": round(
                _mean([r["lns_gap_pct"] for r in sub
                       if r["lns_gap_pct"] != ""]), 2),
            "greedy_gap_proven_mean_pct": round(
                _mean([r["greedy_gap_pct"] for r in proven]), 2),
            "lns_gap_proven_mean_pct": round(
                _mean([r["lns_gap_pct"] for r in proven]), 2),
            "raw_v2_valid": len(valid_raw),
        })

    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(out_raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(out_sum, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    Lg = ["=" * 78,
          "Exact optimality gap on small instances (CP-SAT)",
          "=" * 78,
          f"sizes={SIZES} seeds={N_SEEDS} base {SEED_BASE} "
          f"max_cust={MAX_CUST} time_limit={TIME_LIMIT:.0f}s"]
    Lg.extend(SI.env_lines())
    Lg.append("")
    Lg.append("gap = (heuristic - optimum) / optimum; the optimum is the physical")
    Lg.append("FSTSP model optimum (no overlapping sorties). Where the run is not")
    Lg.append("proven optimal the value is an upper bound on the optimum, so the")
    Lg.append("gap is a lower bound on the true gap.")
    Lg.append("")
    for srow in summary:
        Lg.append(f"  N={srow['size']:2d}: proven {srow['n_opt_proven']}/"
                  f"{srow['n_instances']} | greedy gap "
                  f"{srow['greedy_gap_mean_pct']:6.2f}% | LNS gap "
                  f"{srow['lns_gap_mean_pct']:6.2f}% | "
                  f"proven-only: greedy {srow['greedy_gap_proven_mean_pct']:.2f}%, "
                  f"LNS {srow['lns_gap_proven_mean_pct']:.2f}% | "
                  f"raw V2 plan valid {srow['raw_v2_valid']}/{srow['n_instances']}")
    text = "\n".join(Lg)
    with open(out_txt, "w") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]\n[summary -> {out_sum}]\n[log -> {out_txt}]")


if __name__ == "__main__":
    main()
