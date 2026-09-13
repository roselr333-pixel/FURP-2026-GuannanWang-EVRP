"""
Week 7 — Improvement + Ablation.

The "improvement story" from week07_fstsp_repro was: my ground-air
collaborative heuristic (multi-customer drone flights, up to 2 customers per
sortie, one stop may launch several sorties) beats the published M&C (2015)
FSTSP heuristic (single-customer flights) by ~8-22% on identical instances.

This module turns that into the W7 deliverable the project page asks for:
"test ONE improvement with fair comparisons" + an ablation that shows WHICH
design choice drives the gain.

I keep ONE shared evaluator (the serial-drone FSTSP completion time from
week07_fstsp_repro) so every configuration is compared apples-to-apples, and I
vary exactly two knobs:

  knob A: max customers served by a single drone sortie  -> 1 / 2 / 3
  knob B: can one truck stop launch/recover more than one sortie? -> yes / no

Five configurations (all on the same 40 instances, same seeds, same evaluator):

  C0  published   : M&C (2015) insertion heuristic -- single customer/sortie.
                   This is the genuine published baseline.
  C1  V2 (current): my heuristic, max_cust=2, multi-takeoff ON, sync ON.
                   The improved method.
  C2  abl_cap1    : my framework, max_cust=1, multi-takeoff ON.
                   Sanity check: with cap=1 it should reproduce C0 (published),
                   confirming the only real difference between my method and the
                   baseline is the multi-customer capability.
  C3  abl_notakeoff: my framework, max_cust=2, multi-takeoff OFF.
                   Isolates the contribution of reusing a stop for several
                   launches.
  C4  imp_cap3    : my framework, max_cust=3, multi-takeoff ON.
                   A forward "improvement attempt" pushed one step further;
                   reported as measured (may or may not help).

Metrics per instance: truck-only completion time (no drone), each config's
completion time, % improvement vs truck-only, # customers offloaded, runtime.

Run:
  python src/experiments/week07_improvement_ablation.py
"""

import os
import sys
import time
import csv
import itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7   # reuse the shared FSTSP evaluator

V_T = w6.V_T
V_D = w6.V_D
SERVICE = w6.SERVICE
R_D = w6.R_D


# ---------------------------------------------------------------------------
# Parameterized version of my V2 greedy. Same "route then re-assign" loop and
# same exact sequential evaluator as week07; only the two knobs vary.
# ---------------------------------------------------------------------------
def my_v2_param(inst, max_cust=2, multi_takeoff=True, drone_range=None):
    rd = drone_range if drone_range is not None else R_D
    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    drone_trips = []          # (launch, custs_tuple, recover)
    offloaded = set()
    protected = set()         # launch/recovery nodes may not later be offloaded
    blocked = set()           # (only when multi_takeoff OFF) stops already used

    def usable_stop(node):
        # A launch/recovery node must NOT itself be offloaded (protected), but
        # it MAY be reused as a launch/recovery for another sortie -- that is
        # exactly what "multi-takeoff" means. So in multi-takeoff mode every
        # truck node is usable here; only the single-takeoff mode blocks reuse.
        if multi_takeoff:
            return True
        return node not in blocked

    while True:
        base = f7.fstsp_makespan(inst, route, drone_trips)
        best = None           # (true_net, ln, rn, custs)
        n = len(route)
        for i_idx in range(n - 1):
            ln = route[i_idx]
            if not usable_stop(ln):
                continue
            for j_idx in range(i_idx + 2, n):
                rn = route[j_idx]
                if not usable_stop(rn):
                    continue
                cands = [route[p] for p in range(i_idx + 1, j_idx)
                         if route[p] != 0 and route[p] not in offloaded
                         and route[p] not in protected]
                if not cands:
                    continue
                tt_lr = f7._truck_travel(inst, route, i_idx, j_idx)

                # ---- build candidate subsets of size 1..max_cust ----
                subsets = []
                if max_cust >= 1:
                    for c in cands:
                        subsets.append((c,))
                if max_cust >= 2 and len(cands) >= 2:
                    for x in range(len(cands)):
                        for y in range(x + 1, len(cands)):
                            subsets.append((cands[x], cands[y]))
                            subsets.append((cands[y], cands[x]))
                if max_cust >= 3 and len(cands) >= 3:
                    for trio in itertools.combinations(cands, 3):
                        for perm in itertools.permutations(trio):
                            subsets.append(tuple(perm))

                for custs in subsets:
                    # leg-distance quick prune (each leg must fit in range)
                    ok = True
                    prev = ln
                    for c in custs:
                        if w6.dist(inst, prev, c) > rd:
                            ok = False
                            break
                        prev = c
                    if ok and w6.dist(inst, prev, rn) > rd:
                        ok = False
                    if not ok:
                        continue
                    d = sum(w6.dist(inst, (ln, *custs, rn)[p],
                                    (ln, *custs, rn)[p + 1])
                            for p in range(len(custs) + 1))
                    if d > rd:
                        continue
                    s = sum(f7._remove_saving(inst, route, c) for c in custs)
                    flight = d / V_D + SERVICE * len(custs)
                    delay = max(0.0, flight - (tt_lr - s))
                    if s - delay <= 0:
                        continue
                    new_route = [x for x in route if x not in custs]
                    new_trips = drone_trips + [(ln, custs, rn)]
                    true_net = base - f7.fstsp_makespan(inst, new_route,
                                                        new_trips)
                    if true_net > 0 and (best is None
                                         or true_net > best[0]):
                        best = (true_net, ln, rn, custs)
        if best is None:
            break
        _, ln, rn, custs = best
        for c in custs:
            offloaded.add(c)
        protected.add(ln)
        protected.add(rn)
        if not multi_takeoff:
            blocked.add(ln)
            blocked.add(rn)
        drone_trips.append((ln, custs, rn))
        route = [x for x in route if x not in custs]
    return route, drone_trips, offloaded


# ---------------------------------------------------------------------------
# configuration dispatch
# ---------------------------------------------------------------------------
CONFIGS = {
    "published":   lambda inst: f7.fstsp_insertion(inst),
    "v2":          lambda inst: my_v2_param(inst, max_cust=2,
                                            multi_takeoff=True),
    "abl_cap1":    lambda inst: my_v2_param(inst, max_cust=1,
                                            multi_takeoff=True),
    "abl_notakeoff": lambda inst: my_v2_param(inst, max_cust=2,
                                              multi_takeoff=False),
    "imp_cap3":    lambda inst: my_v2_param(inst, max_cust=3,
                                            multi_takeoff=True),
}


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week07_ablation_raw.csv")
    out_summary = os.path.join(res_dir, "week07_ablation_summary.csv")
    out_txt = os.path.join(res_dir, "week07_ablation_log.txt")

    N_SEEDS = 10
    SIZES = [8, 12, 16, 20]
    SEED_BASE = 20260720     # identical seeds as the week06/07 multi-seed runs

    L = []
    L.append("=" * 78)
    L.append("WEEK 7 — Improvement + Ablation (ground-air collaborative)")
    L.append("=" * 78)
    L.append(f"seeds={N_SEEDS} (base {SEED_BASE}..{SEED_BASE + N_SEEDS - 1})  "
             f"sizes={SIZES}")
    L.append(f"truck_speed={V_T}  drone_speed={V_D}  drone_range={R_D}  "
             f"service={SERVICE}")
    L.append("shared evaluator: FSTSP completion time, ONE serial drone, "
             "sync enforced")
    L.append("configs: " + ", ".join(CONFIGS.keys()))
    L.append(f"total instances = {N_SEEDS * len(SIZES)} x {len(CONFIGS)} "
             f"configs = {N_SEEDS * len(SIZES) * len(CONFIGS)} runs")
    L.append("")

    raw_rows = []
    acc = {n: {c: [] for c in CONFIGS} for n in SIZES}
    acc_truck = {n: [] for n in SIZES}

    for n in SIZES:
        L.append(f"=== size N={n} ===")
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)
            truck_route = [0] + w6.nn_order(inst,
                              list(inst["customers"].keys())) + [0]
            r0 = f7.fstsp_makespan(inst, truck_route, [])
            acc_truck[n].append(r0)

            row = {"size": n, "seed": seed, "truck_only_mk": round(r0, 1)}
            for cname, fn in CONFIGS.items():
                t0 = time.perf_counter()
                route, trips, off = fn(inst)
                rt = time.perf_counter() - t0
                mk = f7.fstsp_makespan(inst, route, trips)
                imp = (r0 - mk) / r0 * 100 if r0 > 0 else 0.0
                row[f"{cname}_mk"] = round(mk, 1)
                row[f"{cname}_imp_pct"] = round(imp, 1)
                row[f"{cname}_off"] = len(off)
                row[f"{cname}_rt"] = round(rt, 4)
                acc[n][cname].append(mk)
                L.append(
                    f"  seed {seed} [{cname:14s}] mk={mk:7.1f} "
                    f"({imp:5.1f}%) off={len(off)}/{n} {rt:.3f}s")
            raw_rows.append(row)
        L.append("")

    # ---- aggregate ----
    L.append("=" * 78)
    L.append("AGGREGATE (mean over seeds per size)")
    L.append("=" * 78)
    summary_rows = []
    for n in SIZES:
        t = acc_truck[n]
        srow = {
            "size": n,
            "n_instances": N_SEEDS,
            "truck_only_makespan": round(_mean(t), 1),
        }
        for cname in CONFIGS:
            vals = acc[n][cname]
            mk = _mean(vals)
            imp = _mean([(a - b) / a * 100 for a, b in zip(t, vals) if a > 0])
            off = _mean([r[f"{cname}_off"] for r in raw_rows
                         if r["size"] == n])
            rt = _mean([r[f"{cname}_rt"] for r in raw_rows
                        if r["size"] == n])
            srow[f"{cname}_makespan"] = round(mk, 1)
            srow[f"{cname}_imp_vs_truck_pct"] = round(imp, 1)
            srow[f"{cname}_offloaded"] = round(off, 1)
            srow[f"{cname}_offload_rate_pct"] = round(off / n * 100, 1)
            srow[f"{cname}_runtime_mean"] = round(rt, 4)

        # decomposition (in improvement %-points vs truck-only)
        def impc(c):
            return srow[f"{c}_imp_vs_truck_pct"]
        srow["gain_multicust_pp"] = round(impc("v2") - impc("abl_cap1"), 1)
        srow["gain_notakeoff_pp"] = round(impc("v2") - impc("abl_notakeoff"), 1)
        srow["gain_cap3_pp"] = round(impc("imp_cap3") - impc("v2"), 1)
        summary_rows.append(srow)
        L.append(
            f"  N={n}: truck={srow['truck_only_makespan']:7.1f}  "
            f"published={srow['published_makespan']:7.1f} "
            f"({impc('published'):5.1f}%)  "
            f"v2={srow['v2_makespan']:7.1f} ({impc('v2'):5.1f}%)  "
            f"abl_cap1={srow['abl_cap1_makespan']:7.1f} "
            f"({impc('abl_cap1'):5.1f}%)  "
            f"abl_notakeoff={srow['abl_notakeoff_makespan']:7.1f} "
            f"({impc('abl_notakeoff'):5.1f}%)  "
            f"imp_cap3={srow['imp_cap3_makespan']:7.1f} "
            f"({impc('imp_cap3'):5.1f}%)")
        L.append(
            f"      decomp: multi-customer +{srow['gain_multicust_pp']}pp, "
            f"multi-takeoff +{srow['gain_notakeoff_pp']}pp, "
            f"cap3 +{srow['gain_cap3_pp']}pp")
    L.append("")

    # ---- write csv ----
    with open(out_raw, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        w.writeheader()
        for row in raw_rows:
            w.writerow(row)
    with open(out_summary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)

    text = "\n".join(L)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[summary -> {out_summary}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
