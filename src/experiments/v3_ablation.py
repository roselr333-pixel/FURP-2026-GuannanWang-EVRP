"""
Core ablation on the V3 model (electric truck + drone + charging + time windows).

The five-configuration ablation in week07_improvement_ablation attributes the
collaborative gain to multi-customer sorties, and week07_ablation_std re-runs it
on standard Solomon topologies. Both live on the FSTSP evaluator, which has no
battery and no time windows: the truck is an unlimited-range vehicle.

This runner asks whether the same attribution survives on the V3 model, where the
truck is electric, may detour to recharge, and customers have time windows.

Configurations (same instances, same seeds, same evaluator as v3_ev_collab.py):

  cap1       my greedy, one customer per sortie, a stop may serve several sorties
  v2         my greedy, up to two customers per sortie, stop reuse on
  notakeoff  my greedy, up to two customers per sortie, stop reuse off
  cap3       my greedy, up to three customers per sortie, stop reuse on

The anchor is V1 (truck-only EV, no drone). The decomposition is reported the
same way as the FSTSP ablation, in percentage points of the improvement over V1:

  multi-customer = v2 - cap1,   multi-takeoff = v2 - notakeoff,   cap3 = cap3 - v2

Every configuration optimises the same penalised objective the V3 greedy uses
(makespan + 1000 x time-window violations), so the raw makespan is reported next
to the violation count: a configuration is only better if it wins on both.

Self-check: with an empty sortie set the V3 evaluator must reproduce the week06
truck-only EV makespan, violations and recharge count exactly; the runner asserts
this on every instance.

Run:
  python src/experiments/v3_ablation.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import v3_ev_collab as v3
import stat_tests as ST
import sysinfo as SI

CONFIGS = {
    "cap1": lambda inst: v3.v3_greedy(inst, max_cust=1, multi_takeoff=True),
    "v2": lambda inst: v3.v3_greedy(inst, max_cust=2, multi_takeoff=True),
    "notakeoff": lambda inst: v3.v3_greedy(inst, max_cust=2,
                                           multi_takeoff=False),
    "cap3": lambda inst: v3.v3_greedy(inst, max_cust=3, multi_takeoff=True),
}
SIZES = [8, 12, 16, 20]
N_SEEDS = 10
SEED_BASE = 20260720          # same seeds as v3_ev_collab.py


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "v3_ablation_raw.csv")
    out_summary = os.path.join(res_dir, "v3_ablation_summary.csv")
    out_stats = os.path.join(res_dir, "v3_ablation_stat_tests.csv")
    out_txt = os.path.join(res_dir, "v3_ablation_log.txt")

    L = []
    L.append("=" * 78)
    L.append("V3 (electric truck + drone + charging + time windows) -- core "
             "ablation")
    L.append("=" * 78)
    L.append(f"sizes={SIZES}  seeds={N_SEEDS} (base {SEED_BASE}.."
             f"{SEED_BASE + N_SEEDS - 1})")
    L.append(f"configs={list(CONFIGS)}  anchor=V1 (truck-only EV)")
    L.append(f"truck_speed={w6.V_T}  drone_speed={w6.V_D}  "
             f"drone_range={w6.R_D}  battery={w6.Q_DEFAULT}  "
             f"recharge={w6.RECHARGE}  service={w6.SERVICE}")
    L.extend(SI.env_lines())
    L.append("")

    raw_rows = []
    per_cfg = {c: {n: [] for n in SIZES} for c in CONFIGS}
    anchor = {n: [] for n in SIZES}
    checks = 0

    for n in SIZES:
        L.append(f"=== size N={n} ===")
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)
            all_c = list(inst["customers"].keys())

            # anchor: truck-only electric vehicle (week06's own EV route)
            v1 = w6.truck_ev_route(inst, all_c, allow_recharge=True)
            anchor[n].append(v1["makespan"])

            # self-check: the V3 evaluator with no sorties must reproduce it
            plain = [0] + w6.nn_order(inst, all_c) + [0]
            chk = v3.ev_collab(inst, plain, [])
            assert abs(chk["makespan"] - v1["makespan"]) < 1e-6, (
                n, seed, chk["makespan"], v1["makespan"])
            assert chk["tw_viol"] == v1["tw_viol"]
            assert chk["recharges"] == v1["recharges"]
            checks += 1

            row = {"size": n, "seed": seed,
                   "V1_makespan": round(v1["makespan"], 1),
                   "V1_tw_viol": v1["tw_viol"],
                   "V1_recharges": v1["recharges"]}
            for cname, fn in CONFIGS.items():
                t0 = time.perf_counter()
                route, trips, off = fn(inst)
                rt = time.perf_counter() - t0
                e = v3.ev_collab(inst, route, trips)
                imp = ((v1["makespan"] - e["makespan"]) / v1["makespan"] * 100
                       if v1["makespan"] > 0 else 0.0)
                row[f"{cname}_makespan"] = round(e["makespan"], 1)
                row[f"{cname}_imp_vs_V1_pct"] = round(imp, 1)
                row[f"{cname}_offloaded"] = len(off)
                row[f"{cname}_trips"] = len(trips)
                row[f"{cname}_tw_viol"] = e["tw_viol"]
                row[f"{cname}_recharges"] = e["recharges"]
                row[f"{cname}_obj"] = round(e["makespan"]
                                            + v3.TW_PENALTY * e["tw_viol"], 1)
                row[f"{cname}_feasible"] = (not e["energy_inf"])
                row[f"{cname}_runtime_s"] = round(rt, 4)
                per_cfg[cname][n].append(e["makespan"])
            L.append(f"  seed {seed}: V1={v1['makespan']:8.1f}  "
                     f"cap1={row['cap1_makespan']:8.1f}  "
                     f"v2={row['v2_makespan']:8.1f}  "
                     f"notakeoff={row['notakeoff_makespan']:8.1f}  "
                     f"cap3={row['cap3_makespan']:8.1f}  "
                     f"off(v2)={row['v2_offloaded']}/{n}  "
                     f"t={row['v2_runtime_s']:.2f}s")
            raw_rows.append(row)
        L.append("")

    # ---- aggregate + decomposition ----
    L.append("=" * 78)
    L.append("AGGREGATE (mean over seeds per size)")
    L.append("=" * 78)
    summary_rows = []
    for n in SIZES:
        t = anchor[n]
        srow = {"size": n, "n_instances": len(t),
                "V1_makespan": round(_mean(t), 1),
                "V1_tw_viol": round(_mean([r["V1_tw_viol"] for r in raw_rows
                                           if r["size"] == n]), 1)}
        for cname in CONFIGS:
            mk = [r[f"{cname}_makespan"] for r in raw_rows if r["size"] == n]
            imp = _mean([(a - b) / a * 100 for a, b in zip(t, mk)])
            srow[f"{cname}_makespan"] = round(_mean(mk), 1)
            srow[f"{cname}_imp_vs_V1_pct"] = round(imp, 1)
            srow[f"{cname}_offloaded"] = round(
                _mean([r[f"{cname}_offloaded"] for r in raw_rows
                       if r["size"] == n]), 1)
            srow[f"{cname}_tw_viol"] = round(
                _mean([r[f"{cname}_tw_viol"] for r in raw_rows
                       if r["size"] == n]), 1)
            srow[f"{cname}_feas_rate"] = round(
                _mean([1.0 if r[f"{cname}_feasible"] else 0.0
                       for r in raw_rows if r["size"] == n]), 3)
        impc = lambda c: srow[f"{c}_imp_vs_V1_pct"]      # noqa: E731
        srow["gain_multicust_pp"] = round(impc("v2") - impc("cap1"), 1)
        srow["gain_notakeoff_pp"] = round(impc("v2") - impc("notakeoff"), 1)
        srow["gain_cap3_pp"] = round(impc("cap3") - impc("v2"), 1)
        summary_rows.append(srow)
        L.append(
            f"  N={n}: V1={srow['V1_makespan']:8.1f}  "
            f"cap1={srow['cap1_makespan']:8.1f} ({impc('cap1'):5.1f}%)  "
            f"v2={srow['v2_makespan']:8.1f} ({impc('v2'):5.1f}%)  "
            f"notakeoff={srow['notakeoff_makespan']:8.1f} "
            f"({impc('notakeoff'):5.1f}%)  "
            f"cap3={srow['cap3_makespan']:8.1f} ({impc('cap3'):5.1f}%)")
        L.append(
            f"      decomp: multi-customer {srow['gain_multicust_pp']:+}pp, "
            f"multi-takeoff {srow['gain_notakeoff_pp']:+}pp, "
            f"cap3 {srow['gain_cap3_pp']:+}pp")
        L.append(
            f"      TW violations: V1 {srow['V1_tw_viol']}  "
            f"cap1 {srow['cap1_tw_viol']}  v2 {srow['v2_tw_viol']}  "
            f"notakeoff {srow['notakeoff_tw_viol']}  "
            f"cap3 {srow['cap3_tw_viol']}")
    L.append("")

    # ---- paired significance tests (all sizes pooled) ----
    L.append("=" * 78)
    L.append("PAIRED WILCOXON (all sizes pooled; negative mean diff = first "
             "is better)")
    L.append("=" * 78)
    stat_rows = []
    for label, a, b in (("v2 vs cap1 (multi-customer)", "v2", "cap1"),
                        ("v2 vs notakeoff (stop reuse)", "v2", "notakeoff"),
                        ("cap3 vs v2 (cap3)", "cap3", "v2")):
        aa = [r[f"{a}_makespan"] for r in raw_rows]
        bb = [r[f"{b}_makespan"] for r in raw_rows]
        res = ST.wilcoxon_signed_rank(aa, bb)
        stat_rows.append({"comparison": label, "n_pairs": res["n_pairs"],
                          "n_nonzero": res["n_nonzero"],
                          "mean_diff": round(res["mean_diff"], 2),
                          "median_diff": round(res["median_diff"], 2),
                          "p_value": res["p_value"],
                          "sig_0.05": "yes" if res["p_value"] < 0.05 else "no"})
        L.append(f"  {label:34s} n={res['n_nonzero']:3d} "
                 f"mean_diff={res['mean_diff']:8.2f} "
                 f"p={res['p_value']:.3g} "
                 f"{'sig' if res['p_value'] < 0.05 else 'not sig'}")
    L.append("")
    L.append(f"self-check: V3 evaluator with no sorties == week06 truck-only EV "
             f"on {checks}/{checks} instances (makespan, TW violations, "
             f"recharges)")
    L.append("")

    with open(out_raw, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        w.writeheader()
        w.writerows(raw_rows)
    with open(out_summary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)
    with open(out_stats, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(stat_rows[0].keys()))
        w.writeheader()
        w.writerows(stat_rows)

    text = "\n".join(L)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[summary -> {out_summary}]")
    print(f"[stat tests -> {out_stats}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
