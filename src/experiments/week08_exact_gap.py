"""
Exact optimality gap on small instances (CP-SAT, warm-started).

The project pages kept noting that "how far the heuristic is from the optimum is
not quantified". This runner quantifies it on small instances. For each instance
it computes

  * the EXACT model of the physical FSTSP problem (cpsat_fstsp.solve_exact),
    warm-started with the best plan my heuristics found: the plan is passed both
    as an objective cut-off (`upper_bound`) and as a CP-SAT hint, so the
    solver starts from a feasible plan and only has to prove optimality;
  * my V2 greedy restricted to that model (cpsat_fstsp.clean_greedy);
  * the LNS run on that model (week08_lns.lns with the physical evaluator).

For every instance the log reports

  * the best FEASIBLE plan CP-SAT found, and whether optimality was proved;
  * the certified lower bound on the optimum (CP-SAT's `BestObjectiveBound`,
    shifted down by the model's 1/SC discretisation so that it stays a true
    bound), flagged as trivial when it is still 0;
  * the gap of my greedy and of the LNS to the best plan found -- a lower bound on
    their true gap -- and, when the dual bound is non-trivial, the CERTIFIED gap,
    which is an upper bound on the true gap.

Proven-optimal runs are flagged; where CP-SAT hits the time limit the returned
value is a feasible solution, so the reported gap is then a lower bound on the
true gap (stated in the log).

Run:
  python src/experiments/week08_exact_gap.py
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab
import week08_lns as L
import cpsat_fstsp as X
import sysinfo as SI

SIZES = [8, 10, 12, 14, 16]
N_SEEDS = 5
SEED_BASE = 20260720
MAX_CUST = 2
NUM_WORKERS = 8
# per-size time budget: n=8 is the size where optimality is actually proved, so it
# gets a budget comfortably above its ~10-35s proof times; from n=10 on the solver
# only returns feasible plans (its dual bound stays trivial), so more time buys a
# slightly better incumbent and nothing else
TIME_LIMIT = {8: 120.0, 10: 60.0, 12: 60.0, 14: 60.0, 16: 60.0}


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def _grid_tolerance(n):
    """Conservative shift that makes the model's lower bound valid for the
    physical model: at most half a time step per truck arc and per sortie."""
    return 0.5 / X.SC * (2 * n + 1)


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
        limit = TIME_LIMIT[n]
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)

            # the project's own V2 heuristic (shared evaluator) and whether the
            # plan it produces is physically valid at all
            r2, t2, _ = ab.my_v2_param(inst, max_cust=2, multi_takeoff=True)
            v2_raw = f7.fstsp_makespan(inst, r2, t2)
            v2_raw_valid = X.clean_simulate(inst, r2, t2)[0]

            # physical model: clean greedy + LNS
            gr, gt, _ = X.clean_greedy(inst, max_cust=MAX_CUST)
            mk_greedy = X.fstsp_makespan_clean(inst, gr, gt)
            lr, lt, _mk, _ = L.lns(
                inst, n, seed=seed, max_cust=MAX_CUST, eval_fn=helper,
                greedy_fn=lambda i: X.clean_greedy(i, max_cust=MAX_CUST))
            mk_lns = X.fstsp_makespan_clean(inst, lr, lt)

            # warm start: the better of the two plans is handed to CP-SAT
            if mk_lns <= mk_greedy:
                h_route, h_trips, best_known = lr, lt, mk_lns
            else:
                h_route, h_trips, best_known = gr, gt, mk_greedy

            res_ex = X.solve_exact(inst, max_cust=MAX_CUST,
                                   time_limit=limit, num_workers=NUM_WORKERS,
                                   upper_bound=best_known,
                                   hint=(h_route, h_trips))
            incumbent = res_ex["makespan"]
            bound = res_ex["bound"]
            bound_safe = (max(0.0, bound - _grid_tolerance(n))
                          if bound is not None else None)
            opt_phys = ""
            opt_phys_valid = ""
            if res_ex["route"] is not None:
                chk = X.fstsp_makespan_clean(inst, res_ex["route"],
                                             res_ex["trips"])
                opt_phys = round(chk, 2) if chk != X.INF else ""
                valid = (chk != X.INF and abs(chk - incumbent)
                         <= X._rounding_tolerance(res_ex["route"],
                                                  res_ex["trips"]))
                opt_phys_valid = "yes" if valid else "no"
            row = {
                "size": n, "seed": seed,
                "opt": (round(incumbent, 2) if incumbent is not None else ""),
                "opt_proven": "yes" if res_ex["proven"] else "no",
                "opt_status": res_ex["status"],
                "opt_wall_s": res_ex["wall_s"],
                "opt_phys": opt_phys,
                "opt_phys_valid": opt_phys_valid,
                "opt_bound": (round(bound, 2) if bound is not None else ""),
                "opt_bound_safe": (round(bound_safe, 2)
                                   if bound_safe is not None else ""),
                "opt_bound_nontrivial": ("yes"
                                         if bound_safe is not None
                                         and bound_safe > 1e-6 else "no"),
                "greedy_mk": round(mk_greedy, 2),
                "lns_mk": round(mk_lns, 2),
                "best_known": round(best_known, 2),
                "cp_sat_improved_pct": (round((best_known - incumbent)
                                              / best_known * 100, 2)
                                        if incumbent else ""),
                "greedy_gap_pct": (round((mk_greedy - incumbent) / incumbent
                                         * 100, 2)
                                   if incumbent else ""),
                "lns_gap_pct": (round((mk_lns - incumbent) / incumbent * 100, 2)
                                if incumbent else ""),
                "certified_gap_pct": (round((mk_lns - bound_safe) / bound_safe
                                            * 100, 2)
                                      if bound_safe and bound_safe > 1e-6
                                      else ""),
                "v2_raw_mk": round(v2_raw, 2),
                "v2_raw_plan_valid": "yes" if v2_raw_valid else "no",
                "n_sorties": res_ex["n_sorties"],
            }
            rows.append(row)
            print(f"n={n} seed={seed}: best feasible={row['opt']} "
                  f"({row['opt_status']}, {row['opt_wall_s']}s, "
                  f"phys valid={row['opt_phys_valid']}) | "
                  f"bound={row['opt_bound']} "
                  f"({'nontrivial' if row['opt_bound_nontrivial'] == 'yes' else 'trivial'})"
                  f" | CP-SAT beats heuristics by "
                  f"{row['cp_sat_improved_pct']}% | greedy "
                  f"{row['greedy_gap_pct']}% LNS {row['lns_gap_pct']}% "
                  f"certified {row['certified_gap_pct']}% | "
                  f"raw V2 valid={row['v2_raw_plan_valid']}", flush=True)

    summary = []
    for n in SIZES:
        sub = [r for r in rows if r["size"] == n]
        proven = [r for r in sub if r["opt_proven"] == "yes"]
        valid_raw = [r for r in sub if r["v2_raw_plan_valid"] == "yes"]
        cert = [r["certified_gap_pct"] for r in sub
                if r["certified_gap_pct"] != ""]
        summary.append({
            "size": n, "time_limit_s": TIME_LIMIT[n],
            "n_instances": len(sub),
            "n_opt_proven": len(proven),
            "n_feasible": len([r for r in sub if r["opt"] != ""]),
            "n_bound_nontrivial": len([r for r in sub
                                       if r["opt_bound_nontrivial"] == "yes"]),
            "greedy_gap_mean_pct": round(
                _mean([r["greedy_gap_pct"] for r in sub
                       if r["greedy_gap_pct"] != ""]), 2),
            "lns_gap_mean_pct": round(
                _mean([r["lns_gap_pct"] for r in sub
                       if r["lns_gap_pct"] != ""]), 2),
            "certified_gap_mean_pct": (round(_mean(cert), 2) if cert else ""),
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
    with open(out_raw, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(out_sum, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    Lg = ["=" * 78,
          "Exact optimality gap on small instances (CP-SAT, warm-started)",
          "=" * 78,
          f"sizes={SIZES} seeds={N_SEEDS} base {SEED_BASE} "
          f"max_cust={MAX_CUST} workers={NUM_WORKERS}",
          "per-size time limit (s): "
          + ", ".join(f"n={n}:{TIME_LIMIT[n]:.0f}" for n in SIZES)]
    Lg.extend(SI.env_lines())
    Lg.append("")
    Lg.append("The best plan my heuristics found is passed to CP-SAT both as an")
    Lg.append("objective cut-off and as a hint, so the solver starts feasible and")
    Lg.append("only has to prove optimality.")
    Lg.append("")
    Lg.append("gap = (heuristic - best feasible plan) / best feasible plan. Where")
    Lg.append("optimality is not proved the best feasible plan is an upper bound on")
    Lg.append("the optimum, so that gap is a LOWER bound on the true gap. The")
    Lg.append("certified gap uses the dual bound instead (shifted by the 1/SC")
    Lg.append("discretisation), so it is an UPPER bound on the true gap. In practice")
    Lg.append("the dual bound stays far below the primal (e.g. 27.6 against an")
    Lg.append("incumbent of 217 at n=10 in 300s), so the column documents how weak")
    Lg.append("the relaxation still is rather than certifying a useful gap.")
    Lg.append("cp_sat_improved_pct = how much the CP-SAT plan beats the best plan my")
    Lg.append("heuristics found (0.00 means the heuristic plan was not improved on).")
    Lg.append("")
    for srow in summary:
        Lg.append(f"  N={srow['size']:2d}: proven {srow['n_opt_proven']}/"
                  f"{srow['n_instances']} | feasible {srow['n_feasible']}/"
                  f"{srow['n_instances']} | dual bound non-trivial "
                  f"{srow['n_bound_nontrivial']}/{srow['n_instances']} | "
                  f"greedy gap {srow['greedy_gap_mean_pct']:6.2f}% | LNS gap "
                  f"{srow['lns_gap_mean_pct']:6.2f}% | certified LNS gap "
                  f"{srow['certified_gap_mean_pct']} | "
                  f"raw V2 plan valid {srow['raw_v2_valid']}/{srow['n_instances']}")
    text = "\n".join(Lg)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]\n[summary -> {out_sum}]\n[log -> {out_txt}]")


if __name__ == "__main__":
    main()
