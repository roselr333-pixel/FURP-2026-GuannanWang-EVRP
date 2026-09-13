"""
Week 8 (extension) -- multi-drone truck-drone collaboration.

The W8 LNS note lists "single drone" as a limitation: every earlier result runs
one serial drone carried by the truck. This module breaks that limitation by
supporting K parallel serial drones and re-running the greedy + LNS for K = 1, 2,
3 on the same instances, so the drone-count design variable can be read off.

Model: the truck carries K drones. Each sortie is served by whichever drone can
start earliest; a drone is serial (its next sortie starts only after the previous
one is recovered); the truck waits at a recovery node until the sortie landing
there has arrived. K=1 reduces to the single-drone FSTSP evaluator used in W7/W8
(checked to be numerically identical).

Everything else (instances, seeds, iteration budget, destroy/repair operators)
is the same as week08_lns, so the only thing that changes across a row is K.

Run:
  python src/experiments/week08_multidrone.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week08_lns as L
import sysinfo as SI

V_D = w6.V_D
SERVICE = w6.SERVICE
R_D = w6.R_D

DRONES = [1, 2, 3]
SIZES = [8, 12, 16, 20, 30, 50]
N_SEEDS = 10
SEED_BASE = 20260720


def greedy_multi(inst, n_drones, max_cust=2, rd=R_D):
    """Greedy V2 constructor for `n_drones` parallel serial drones. Same
    selection loop as week07_improvement_ablation.my_v2_param, but every move is
    validated with the K-drone evaluator."""
    def ev(route, trips):
        return f7.fstsp_makespan_multi(inst, route, trips, n_drones)

    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    drone_trips = []
    offloaded = set()
    protected = set()

    while True:
        base = ev(route, drone_trips)
        best = None
        n = len(route)
        for i_idx in range(n - 1):
            ln = route[i_idx]
            for j_idx in range(i_idx + 2, n):
                rn = route[j_idx]
                cands = [route[p] for p in range(i_idx + 1, j_idx)
                         if route[p] != 0 and route[p] not in offloaded
                         and route[p] not in protected]
                if not cands:
                    continue
                tt_lr = f7._truck_travel(inst, route, i_idx, j_idx)
                subsets = [(c,) for c in cands]
                if max_cust >= 2 and len(cands) >= 2:
                    for x in range(len(cands)):
                        for y in range(x + 1, len(cands)):
                            subsets.append((cands[x], cands[y]))
                            subsets.append((cands[y], cands[x]))
                if max_cust >= 3 and len(cands) >= 3:
                    for a in range(len(cands)):
                        for b in range(a + 1, len(cands)):
                            for c in range(b + 1, len(cands)):
                                for perm in ((cands[a], cands[b], cands[c]),
                                             (cands[a], cands[c], cands[b]),
                                             (cands[b], cands[a], cands[c]),
                                             (cands[b], cands[c], cands[a]),
                                             (cands[c], cands[a], cands[b]),
                                             (cands[c], cands[b], cands[a])):
                                    subsets.append(perm)
                for custs in subsets:
                    prev, ok = ln, True
                    for cc in custs:
                        if w6.dist(inst, prev, cc) > rd:
                            ok = False
                            break
                        prev = cc
                    if ok and w6.dist(inst, prev, rn) > rd:
                        ok = False
                    if not ok:
                        continue
                    legs = [ln] + list(custs) + [rn]
                    d = sum(w6.dist(inst, legs[p], legs[p + 1])
                            for p in range(len(legs) - 1))
                    if d > rd:
                        continue
                    s = sum(f7._remove_saving(inst, route, cc) for cc in custs)
                    flight = d / V_D + SERVICE * len(custs)
                    delay = max(0.0, flight - (tt_lr - s))
                    if s - delay <= 0:
                        continue
                    new_route = [x for x in route if x not in custs]
                    net = base - ev(new_route, drone_trips + [(ln, custs, rn)])
                    if net > 0 and (best is None or net > best[0]):
                        best = (net, ln, rn, custs)
        if best is None:
            break
        _, ln, rn, custs = best
        for c in custs:
            offloaded.add(c)
        protected.add(ln)
        protected.add(rn)
        drone_trips.append((ln, custs, rn))
        route = [x for x in route if x not in custs]
    return route, drone_trips, offloaded


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    os.makedirs(res, exist_ok=True)
    out_raw = os.path.join(res, "week08_multidrone_raw.csv")
    out_summary = os.path.join(res, "week08_multidrone_summary.csv")
    out_txt = os.path.join(res, "week08_multidrone_log.txt")

    L_ = []
    L_.append("=" * 78)
    L_.append("WEEK 8 (ext) -- multi-drone truck-drone collaboration")
    L_.append("=" * 78)
    L_.append(f"drones K={DRONES}  sizes={SIZES}  seeds={N_SEEDS} "
              f"(base {SEED_BASE})")
    L_.append(f"truck_speed={w6.V_T}  drone_speed={V_D}  drone_range={R_D}  "
              f"service={SERVICE}")
    L_.append("K-drone evaluator: K parallel serial drones; K=1 == W7/W8 "
              "single-drone evaluator")
    L_.extend(SI.env_lines())
    L_.append("")

    raw_rows = []
    for n in SIZES:
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)
            truck_route = [0] + w6.nn_order(inst,
                              list(inst["customers"].keys())) + [0]
            mk_truck = f7.fstsp_makespan(inst, truck_route, [])
            row = {"size": n, "seed": seed, "truck_only_mk": round(mk_truck, 1)}
            for K in DRONES:
                ev = (lambda K: (lambda i, r, t:
                      f7.fstsp_makespan_multi(i, r, t, K)))(K)
                t0 = time.perf_counter()
                g_route, g_trips, g_off = greedy_multi(inst, K)
                mk_g = ev(inst, g_route, g_trips)
                l_route, l_trips, mk_l, _ = L.lns(
                    inst, n, seed=seed, eval_fn=ev,
                    greedy_fn=lambda inst, K=K: greedy_multi(inst, K))
                rt = time.perf_counter() - t0
                row[f"K{K}_greedy_mk"] = round(mk_g, 1)
                row[f"K{K}_greedy_off"] = len(g_off)
                row[f"K{K}_lns_mk"] = round(mk_l, 1)
                row[f"K{K}_lns_off"] = len(l_trips)
                row[f"K{K}_lns_imp_vs_greedy_pct"] = round(
                    (mk_g - mk_l) / mk_g * 100, 2)
                row[f"K{K}_lns_imp_vs_truck_pct"] = round(
                    (mk_truck - mk_l) / mk_truck * 100, 1)
                row[f"K{K}_rt"] = round(rt, 2)
            raw_rows.append(row)
        L_.append(f"=== size N={n} done ===")
    L_.append("")

    # ---- aggregate ----
    L_.append("=" * 78)
    L_.append("AGGREGATE (mean over seeds per size)")
    L_.append("=" * 78)
    summary_rows = []
    for n in SIZES:
        sub = [r for r in raw_rows if r["size"] == n]
        srow = {"size": n, "n_instances": N_SEEDS,
                "truck_only_mk": round(_mean([r["truck_only_mk"]
                                              for r in sub]), 1)}
        for K in DRONES:
            srow[f"K{K}_greedy_mk"] = round(
                _mean([r[f"K{K}_greedy_mk"] for r in sub]), 1)
            srow[f"K{K}_lns_mk"] = round(
                _mean([r[f"K{K}_lns_mk"] for r in sub]), 1)
            srow[f"K{K}_lns_imp_vs_truck_pct"] = round(
                _mean([r[f"K{K}_lns_imp_vs_truck_pct"] for r in sub]), 1)
            srow[f"K{K}_lns_imp_vs_greedy_pct"] = round(
                _mean([r[f"K{K}_lns_imp_vs_greedy_pct"] for r in sub]), 2)
            srow[f"K{K}_lns_off"] = round(
                _mean([r[f"K{K}_lns_off"] for r in sub]), 1)
        summary_rows.append(srow)
        L_.append(
            f"  N={n:2d} truck={srow['truck_only_mk']:7.1f}  " +
            "  ".join(
                f"K{K}: LNS={srow[f'K{K}_lns_mk']:7.1f} "
                f"({srow[f'K{K}_lns_imp_vs_truck_pct']:5.1f}%) "
                f"g={srow[f'K{K}_lns_imp_vs_greedy_pct']:4.1f}%"
                for K in DRONES))
    L_.append("")
    L_.append("Reading: (a) LNS gain vs the K-drone greedy (g); "
              "(b) LNS makespan vs truck-only in %; growing K lowers makespan.")

    with open(out_raw, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        w.writeheader()
        w.writerows(raw_rows)
    with open(out_summary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    text = "\n".join(L_)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]\n[summary -> {out_summary}]\n[log -> {out_txt}]")


if __name__ == "__main__":
    main()
