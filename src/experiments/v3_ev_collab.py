"""
V3 -- electric truck + drone + charging stations + time windows.

The W8 LNS and multi-drone results all live on the FSTSP evaluator, which has
neither time windows nor a battery: the truck is an unlimited-range vehicle and
the only constraints are the drone range and the rendezvous. This module brings
the collaborative model back onto the week06 EVRP-TW setting:

  - the truck has a battery (capacity Q, consumption rho per distance unit) and
    may detour to a charging station for a full recharge (RECHARGE time units);
  - customers have time windows; arriving early means waiting, arriving late is
    counted as a violation;
  - the drone still has a range limit and must be recovered by the truck.

The evaluator takes a truck route that lists CUSTOMERS ONLY (plus the depot
bookends) and inserts the charging-station detours itself, so the same
destroy/repair LNS from week08_lns can be reused unchanged.

Variants compared by the runner:
  V1  truck-only EV (week06 truck_ev_route)      -- the EV baseline
  V3g electric truck + drone, greedy
  V3l electric truck + drone, greedy + LNS

Run:
  python src/experiments/v3_ev_collab.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week08_lns as L

V_T = w6.V_T
V_D = w6.V_D
SERVICE = w6.SERVICE
RECHARGE = w6.RECHARGE
RHO = w6.RHO
R_D = w6.R_D
dist = w6.dist


def ev_collab(inst, route, drone_trips, q=None):
    """Completion time of an electric-truck + drone solution, with charging
    detours and time windows.

    route       : [0, ...customers..., 0]  (charging stops are added here)
    drone_trips : (launch, customers_tuple, recover)
    Returns dict(makespan, truck_makespan, drone_makespan, tw_viol,
                 energy_inf, recharges, total_dist)."""
    Q = q if q is not None else inst["Q"]
    path = [0]
    arr = [0.0]
    battery = float(Q)
    t = 0.0
    recharges = 0
    energy_inf = False
    tw_viol = 0

    for node in route[1:]:
        d = dist(inst, path[-1], node)
        if battery - d * RHO < 0:
            s = w6.nearest_station(inst, path[-1])
            ds = dist(inst, path[-1], s)
            # same assumption as week06's truck_ev_route: the truck can always
            # limp to the nearest station; infeasibility is only flagged when a
            # full battery cannot cover the leg out of the station
            t += ds / V_T + RECHARGE
            battery = float(Q)
            recharges += 1
            path.append(s)
            arr.append(t)
            d = dist(inst, s, node)
            if battery - d * RHO < 0:
                energy_inf = True
        t += d / V_T
        battery -= d * RHO
        if node != 0:
            if t < inst["tw"][node][0]:
                t = inst["tw"][node][0]
            if t > inst["tw"][node][1]:
                tw_viol += 1
            t += SERVICE
        path.append(node)
        arr.append(t)

    drone_free = 0.0
    for ln, custs, rn in sorted(drone_trips,
                                key=lambda tr: 0 if tr[0] == 0
                                else path.index(tr[0])):
        i_pos = 0 if ln == 0 else path.index(ln)
        j_pos = len(path) - 1 if rn == 0 else path.index(rn)
        launch = arr[i_pos]
        legs = [ln] + list(custs) + [rn]
        dsum = sum(dist(inst, legs[k], legs[k + 1])
                   for k in range(len(legs) - 1))
        flight = dsum / V_D + SERVICE * len(custs)
        if dsum > R_D:
            energy_inf = True
        # drone time windows (sequential service)
        tt = launch
        prev = ln
        for c in custs:
            tt += dist(inst, prev, c) / V_D
            if tt < inst["tw"][c][0]:
                tt = inst["tw"][c][0]
            if tt > inst["tw"][c][1]:
                tw_viol += 1
            tt += SERVICE
            prev = c
        landing = launch + flight
        recovery = max(arr[j_pos], landing)
        drone_free = max(drone_free, recovery)
        wait = recovery - arr[j_pos]
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
            t += wait

    return {
        "makespan": max(arr[-1], drone_free),
        "truck_makespan": arr[-1],
        "drone_makespan": drone_free,
        "tw_viol": tw_viol,
        "energy_inf": energy_inf,
        "recharges": recharges,
        "total_dist": sum(dist(inst, path[k], path[k + 1])
                          for k in range(len(path) - 1)),
    }


TW_PENALTY = 1000.0


def ev_lns(inst, route, drone_trips):
    """Scalar objective for the LNS: makespan, with energy-infeasible solutions
    rejected outright and time-window violations heavily penalised."""
    r = ev_collab(inst, route, drone_trips)
    if r["energy_inf"]:
        return float("inf")
    return r["makespan"] + TW_PENALTY * r["tw_viol"]


def v3_greedy(inst, max_cust=2, rd=R_D):
    """Route-and-reassign greedy on the EV + TW + drone model."""
    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    trips = []
    offloaded = set()
    protected = set()
    base = ev_collab(inst, route, trips)
    cur_obj = ev_lns(inst, route, trips)   # penalised objective (TW + energy)

    while True:
        best = None
        for i_pos in range(len(route) - 1):
            for j_pos in range(i_pos + 2, len(route)):
                ln, rn = route[i_pos], route[j_pos]
                cands = [c for c in route[i_pos + 1:j_pos]
                         if c != 0 and c not in protected]
                if not cands:
                    continue
                subsets = [(c,) for c in cands]
                if max_cust >= 2:
                    for a in range(len(cands)):
                        for b in range(a + 1, len(cands)):
                            subsets.append((cands[a], cands[b]))
                            subsets.append((cands[b], cands[a]))
                for custs in subsets:
                    new_route = [x for x in route if x not in custs]
                    new_trips = trips + [(ln, custs, rn)]
                    obj = ev_lns(inst, new_route, new_trips)
                    if obj == float("inf"):
                        continue
                    gain = cur_obj - obj
                    if gain > 1e-9 and (best is None or gain > best[0]):
                        best = (gain, ln, custs, rn)
        if best is None:
            break
        _, ln, custs, rn = best
        route = [x for x in route if x not in custs]
        trips.append((ln, custs, rn))
        offloaded.update(custs)
        protected.add(ln)
        protected.add(rn)
        cur_obj = ev_lns(inst, route, trips)
    return route, trips, offloaded


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    os.makedirs(res, exist_ok=True)
    out_raw = os.path.join(res, "v3_ev_collab_raw.csv")
    out_sum = os.path.join(res, "v3_ev_collab_summary.csv")
    out_txt = os.path.join(res, "v3_ev_collab_log.txt")

    SIZES = [8, 12, 16, 20]
    N_SEEDS = 10
    SEED_BASE = 20260720

    rows = []
    for n in SIZES:
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)

            # V1: truck-only electric vehicle
            v1 = w6.truck_ev_route(inst, list(inst["customers"].keys()),
                                   allow_recharge=True)
            # V3 greedy
            gr, gt, go = v3_greedy(inst)
            g = ev_collab(inst, gr, gt)
            # V3 + LNS
            lr, lt, _, _ = L.lns(inst, n, seed=seed,
                                 eval_fn=ev_lns,
                                 greedy_fn=lambda inst: v3_greedy(inst))
            l = ev_collab(inst, lr, lt)

            rows.append({
                "size": n, "seed": seed,
                "V1_makespan": round(v1["makespan"], 1),
                "V1_tw_viol": v1["tw_viol"],
                "V1_recharges": v1["recharges"],
                "V3g_makespan": round(g["makespan"], 1),
                "V3g_tw_viol": g["tw_viol"],
                "V3g_recharges": g["recharges"],
                "V3g_offloaded": sum(len(c) for _, c, _ in gt),
                "V3l_makespan": round(l["makespan"], 1),
                "V3l_tw_viol": l["tw_viol"],
                "V3l_recharges": l["recharges"],
                "V3l_offloaded": sum(len(c) for _, c, _ in lt),
                "imp_greedy_vs_V1_pct": round(
                    (v1["makespan"] - g["makespan"]) / v1["makespan"] * 100, 1),
                "imp_lns_vs_V1_pct": round(
                    (v1["makespan"] - l["makespan"]) / v1["makespan"] * 100, 1),
                "imp_lns_vs_greedy_pct": round(
                    (g["makespan"] - l["makespan"]) / g["makespan"] * 100, 2),
            })

    summary = []
    for n in SIZES:
        sub = [r for r in rows if r["size"] == n]
        summary.append({
            "size": n, "n_instances": len(sub),
            "V1_makespan": round(_mean([r["V1_makespan"] for r in sub]), 1),
            "V3g_makespan": round(_mean([r["V3g_makespan"] for r in sub]), 1),
            "V3l_makespan": round(_mean([r["V3l_makespan"] for r in sub]), 1),
            "V3g_imp_vs_V1_pct": round(
                _mean([r["imp_greedy_vs_V1_pct"] for r in sub]), 1),
            "V3l_imp_vs_V1_pct": round(
                _mean([r["imp_lns_vs_V1_pct"] for r in sub]), 1),
            "V3l_imp_vs_greedy_pct": round(
                _mean([r["imp_lns_vs_greedy_pct"] for r in sub]), 2),
            "V1_tw_viol": round(_mean([r["V1_tw_viol"] for r in sub]), 1),
            "V3l_tw_viol": round(_mean([r["V3l_tw_viol"] for r in sub]), 1),
            "V1_recharges": round(_mean([r["V1_recharges"] for r in sub]), 1),
            "V3l_recharges": round(_mean([r["V3l_recharges"] for r in sub]), 1),
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
          "V3 -- electric truck + drone + charging + time windows",
          "=" * 78,
          f"sizes={SIZES}  seeds={N_SEEDS}  base {SEED_BASE}",
          "V1 = truck-only EV | V3g = EV+drone greedy | V3l = EV+drone greedy+LNS",
          ""]
    for s in summary:
        Lg.append(f"  N={s['size']:2d}: V1={s['V1_makespan']:8.1f}  "
                  f"V3g={s['V3g_makespan']:8.1f} ({s['V3g_imp_vs_V1_pct']:5.1f}%)  "
                  f"V3l={s['V3l_makespan']:8.1f} ({s['V3l_imp_vs_V1_pct']:5.1f}%)  "
                  f"LNS gain {s['V3l_imp_vs_greedy_pct']:5.2f}%  "
                  f"TWviol V1={s['V1_tw_viol']:.1f} V3l={s['V3l_tw_viol']:.1f}  "
                  f"rechg {s['V1_recharges']:.1f}->{s['V3l_recharges']:.1f}")
    text = "\n".join(Lg)
    with open(out_txt, "w") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]\n[summary -> {out_sum}]\n[log -> {out_txt}]")


if __name__ == "__main__":
    main()
