"""
Week 8 (extension) -- multi-drone truck-drone on STANDARD instances, with an
optimised drone schedule.

This script addresses three limitations listed in the W8 notes at once:

  1. instances: standard Solomon topology (fstsp_instances.make_solomon_fstsp)
     instead of random geometry;
  2. drone count: K = 1/2/3/5 instead of only up to 3;
  3. scheduling: on top of the naive "earliest-available drone" rule, the
     sortie-to-drone assignment is optimised (drone_scheduling: local search,
     and an exact optimum where the sortie count is small).

For every (family, n, K) it records the truck-only makespan, the K-drone greedy,
the K-drone LNS, and -- on the LNS solution -- the makespan under greedy / local
/ optimal scheduling.

Run:
  python src/experiments/week08_multidrone_std.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week08_multidrone as M
import week08_lns as L
import drone_scheduling as S
import fstsp_instances as fi

DRONES = [1, 2, 3, 5]
SIZES = [10, 20, 30, 50]
LNS_SEED = 20260720
OPT_TRIP_CAP = 12          # only run the exact scheduler up to this many sorties


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    os.makedirs(res, exist_ok=True)
    out_raw = os.path.join(res, "week08_multidrone_std_raw.csv")
    out_summary = os.path.join(res, "week08_multidrone_std_summary.csv")
    out_sched = os.path.join(res, "week08_scheduling.csv")
    out_txt = os.path.join(res, "week08_multidrone_std_log.txt")

    Lg = []
    Lg.append("=" * 78)
    Lg.append("WEEK 8 (ext) -- multi-drone on STANDARD (Solomon) instances "
              "+ optimised scheduling")
    Lg.append("=" * 78)
    Lg.append(f"families={fi.FAMILIES}  sizes={SIZES}  drones K={DRONES}")
    Lg.append("instances = Solomon topology, first n customers, rescaled to the "
              "synthetic cloud radius")
    Lg.append("")

    raw_rows = []
    sched_rows = []
    for name in fi.FAMILIES:
        for n in SIZES:
            inst = fi.make_solomon_fstsp(name, n)
            truck_route = [0] + w6.nn_order(inst,
                              list(inst["customers"].keys())) + [0]
            mk_truck = f7.fstsp_makespan(inst, truck_route, [])
            row = {"family": name, "size": n, "truck_only_mk": round(mk_truck, 1)}
            for K in DRONES:
                ev = (lambda K: (lambda i, r, t:
                      f7.fstsp_makespan_multi(i, r, t, K)))(K)
                t0 = time.perf_counter()
                g_route, g_trips, g_off = M.greedy_multi(inst, K)
                mk_g = ev(inst, g_route, g_trips)
                l_route, l_trips, mk_l, _ = L.lns(
                    inst, n, seed=LNS_SEED, eval_fn=ev,
                    greedy_fn=lambda inst, K=K: M.greedy_multi(inst, K))
                rt = time.perf_counter() - t0
                row[f"K{K}_greedy_mk"] = round(mk_g, 1)
                row[f"K{K}_lns_mk"] = round(mk_l, 1)
                row[f"K{K}_lns_off"] = len(l_trips)
                row[f"K{K}_lns_imp_vs_truck_pct"] = round(
                    (mk_truck - mk_l) / mk_truck * 100, 1)
                row[f"K{K}_rt"] = round(rt, 2)

                # scheduling on the LNS solution
                _, mk_gr = S.schedule_greedy(inst, l_route, l_trips, K)
                _, mk_lo = S.schedule_local(inst, l_route, l_trips, K)
                mk_op, proven, has_op = "", False, len(l_trips) <= OPT_TRIP_CAP
                if has_op:
                    _, mk_op, proven = S.schedule_optimal(
                        inst, l_route, l_trips, K, node_limit=120000)
                srow = {
                    "family": name, "size": n, "K": K,
                    "trips": len(l_trips),
                    "sched_greedy_mk": round(mk_gr, 2),
                    "sched_local_mk": round(mk_lo, 2),
                    "sched_optimal_mk": (round(mk_op, 2) if has_op else ""),
                    "optimal_proven": (proven if has_op else ""),
                    "local_gain_pct": round((mk_gr - mk_lo) / mk_gr * 100, 3),
                }
                if has_op:
                    srow["greedy_gap_to_opt_pct"] = round(
                        (mk_gr - mk_op) / mk_op * 100, 3)
                sched_rows.append(srow)
            raw_rows.append(row)
        Lg.append(f"=== family {name} done ===")
    Lg.append("")

    # ---- aggregate by size ----
    Lg.append("=" * 78)
    Lg.append("AGGREGATE by size (mean over families)")
    Lg.append("=" * 78)
    summary_rows = []
    for n in SIZES:
        sub = [r for r in raw_rows if r["size"] == n]
        srow = {"size": n, "n_instances": len(sub),
                "truck_only_mk": round(_mean([r["truck_only_mk"]
                                              for r in sub]), 1)}
        for K in DRONES:
            srow[f"K{K}_lns_mk"] = round(
                _mean([r[f"K{K}_lns_mk"] for r in sub]), 1)
            srow[f"K{K}_lns_imp_vs_truck_pct"] = round(
                _mean([r[f"K{K}_lns_imp_vs_truck_pct"] for r in sub]), 1)
        summary_rows.append(srow)
        Lg.append(f"  N={n:2d} truck={srow['truck_only_mk']:8.1f}  " +
                  "  ".join(f"K{K}: {srow[f'K{K}_lns_mk']:8.1f} "
                            f"({srow[f'K{K}_lns_imp_vs_truck_pct']:5.1f}%)"
                            for K in DRONES))
    Lg.append("")

    # ---- scheduling summary ----
    Lg.append("=" * 78)
    Lg.append("SCHEDULING: greedy (earliest-available) vs local vs optimal")
    Lg.append("=" * 78)
    loc_gains = [r["local_gain_pct"] for r in sched_rows]
    Lg.append(f"  mean local-search gain over the naive rule: "
              f"{_mean(loc_gains):.3f}%  (max {max(loc_gains):.3f}%)")
    opts = [r for r in sched_rows if r["sched_optimal_mk"] != ""]
    if opts:
        gaps = [r["greedy_gap_to_opt_pct"] for r in opts]
        Lg.append(f"  exact-optimal check on {len(opts)} configs "
                  f"(trips <= {OPT_TRIP_CAP}): naive rule is on average "
                  f"{_mean(gaps):.3f}% above optimal (max {max(gaps):.3f}%)")
    else:
        Lg.append("  (no configs small enough for the exact scheduler)")

    with open(out_raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        w.writeheader()
        w.writerows(raw_rows)
    with open(out_summary, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)
    with open(out_sched, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sched_rows[0].keys()))
        w.writeheader()
        w.writerows(sched_rows)

    text = "\n".join(Lg)
    with open(out_txt, "w") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[summary -> {out_summary}]")
    print(f"[scheduling -> {out_sched}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
