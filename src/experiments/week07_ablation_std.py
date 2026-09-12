"""
Week 7 (extension) -- the core ablation on STANDARD (Solomon) instances.

The W6/W7 limitation list says the five-configuration ablation that attributes
the gain ("multi-customer sorties are the main source") was only run on random
geometry, so the attribution could in principle be an artifact of the synthetic
customer cloud. This script re-runs exactly the same five configurations with
exactly the same heuristic code and the same shared evaluator, but on the
official Solomon topologies already in the repo.

Instances: the four distinct spatial families (C101 clustered, C201 clustered
with wider windows, R101 uniform, RC101 mixed) at n = 8/12/16/20. The Solomon
files in this repo share coordinates within a family prefix, so "the first n
customers" would give only 4 point sets per size; to get a real sample I slide a
window of n customers over each instance (start = 0, n, 2n), giving 4 x 3 = 12
genuinely different customer sets per size and 48 instances in total. Every
window is rescaled to the same cloud radius as the synthetic generator at that
n (fstsp_instances.make_solomon_fstsp).

Configurations, unchanged from the synthetic run:

  C0  published    : M&C (2015) insertion heuristic, single customer per sortie
  C1  v2           : my heuristic, max_cust=2, multi-takeoff ON
  C2  abl_cap1     : my framework, max_cust=1, multi-takeoff ON
  C3  abl_notakeoff: my framework, max_cust=2, multi-takeoff OFF
  C4  imp_cap3     : my framework, max_cust=3, multi-takeoff ON

Nothing in the heuristic changes here: this module imports the parameterised
greedy (week07_improvement_ablation.my_v2_param) and its CONFIGS mapping, so the
only difference from the synthetic run is where the customers sit.

Run:
  python src/experiments/week07_ablation_std.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab   # same heuristic, same CONFIGS
import fstsp_instances as fi
import sysinfo as SI

FAMILIES = fi.FAMILIES          # C101, C201, R101, RC101 (the distinct topologies)
WINDOWS = [0, 1, 2]             # customer windows: start = window * n
SIZES = [8, 12, 16, 20]


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week07_ablation_std_raw.csv")
    out_summary = os.path.join(res_dir, "week07_ablation_std_summary.csv")
    out_txt = os.path.join(res_dir, "week07_ablation_std_log.txt")

    n_inst = len(FAMILIES) * len(WINDOWS)

    L = []
    L.append("=" * 78)
    L.append("WEEK 7 (ext) -- core ablation on STANDARD (Solomon) instances")
    L.append("=" * 78)
    L.append(f"families={FAMILIES}  windows per family={WINDOWS} "
             f"(start = window * n)")
    L.append(f"sizes={SIZES}  -> {n_inst} instances per size, "
             f"{n_inst * len(SIZES)} in total, x {len(ab.CONFIGS)} configs = "
             f"{n_inst * len(SIZES) * len(ab.CONFIGS)} runs")
    L.append(f"truck_speed={w6.V_T}  drone_speed={w6.V_D}  "
             f"drone_range={w6.R_D}  service={w6.SERVICE}")
    L.append("shared evaluator: FSTSP completion time, ONE serial drone, "
             "sync enforced")
    L.append("geometry: official Solomon coordinates, rescaled to the synthetic "
             "cloud radius")
    L.extend(SI.env_lines())
    L.append("")

    raw_rows = []
    acc = {n: {c: [] for c in ab.CONFIGS} for n in SIZES}
    acc_truck = {n: [] for n in SIZES}

    for name in FAMILIES:
        for n in SIZES:
            for win in WINDOWS:
                inst = fi.make_solomon_fstsp(name, n, start=win * n)
                truck_route = [0] + w6.nn_order(inst,
                                  list(inst["customers"].keys())) + [0]
                r0 = f7.fstsp_makespan(inst, truck_route, [])
                acc_truck[n].append(r0)
                L.append(f"=== {name} N={n} window={win} "
                         f"(truck-only {r0:.1f}) ===")
                row = {"family": name, "window": win, "size": n,
                       "truck_only_mk": round(r0, 1)}
                for cname, fn in ab.CONFIGS.items():
                    t0 = time.perf_counter()
                    route, trips, off = fn(inst)
                    rt = time.perf_counter() - t0
                    mk = f7.fstsp_makespan(inst, route, trips)
                    imp = (r0 - mk) / r0 * 100 if r0 > 0 else 0.0
                    row[f"{cname}_mk"] = round(mk, 1)
                    row[f"{cname}_imp_pct"] = round(imp, 1)
                    row[f"{cname}_off"] = len(off)
                    row[f"{cname}_runtime_s"] = round(rt, 4)
                    acc[n][cname].append(mk)
                    L.append(f"  [{cname:14s}] mk={mk:7.1f} ({imp:5.1f}%) "
                             f"off={len(off)}/{n} {rt:.3f}s")
                raw_rows.append(row)
        L.append("")

    # ---- aggregate ----
    L.append("=" * 78)
    L.append(f"AGGREGATE (mean over {n_inst} standard instances per size)")
    L.append("=" * 78)
    summary_rows = []
    for n in SIZES:
        t = acc_truck[n]
        srow = {"size": n, "n_instances": len(t),
                "truck_only_makespan": round(_mean(t), 1)}
        for cname in ab.CONFIGS:
            vals = acc[n][cname]
            imp = _mean([(a - b) / a * 100 for a, b in zip(t, vals) if a > 0])
            off = _mean([r[f"{cname}_off"] for r in raw_rows
                         if r["size"] == n])
            rt = _mean([r[f"{cname}_runtime_s"] for r in raw_rows
                        if r["size"] == n])
            srow[f"{cname}_makespan"] = round(_mean(vals), 1)
            srow[f"{cname}_imp_vs_truck_pct"] = round(imp, 1)
            srow[f"{cname}_offloaded"] = round(off, 1)
            srow[f"{cname}_offload_rate_pct"] = round(off / n * 100, 1)
            srow[f"{cname}_runtime_mean"] = round(rt, 4)
        impc = lambda c: srow[f"{c}_imp_vs_truck_pct"]  # noqa: E731
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

    # ---- per-family spread of the main factor ----
    L.append("=" * 78)
    L.append("MULTI-CUSTOMER GAIN BY FAMILY (pp, mean over sizes and windows)")
    L.append("=" * 78)
    for name in FAMILIES:
        sub = [r for r in raw_rows if r["family"] == name]
        L.append(f"  {name}: truck={_mean([r['truck_only_mk'] for r in sub]):7.1f}"
                 f"  published={_mean([r['published_imp_pct'] for r in sub]):5.1f}%"
                 f"  v2={_mean([r['v2_imp_pct'] for r in sub]):5.1f}%"
                 f"  multi-customer gain="
                 f"{_mean([r['v2_imp_pct'] for r in sub]) - _mean([r['abl_cap1_imp_pct'] for r in sub]):5.1f}pp")
    L.append("")

    # ---- does the synthetic attribution survive? ----
    L.append("=" * 78)
    L.append("STANDARD vs SYNTHETIC (same five configs, same evaluator)")
    L.append("=" * 78)
    syn_path = os.path.join(res_dir, "week07_ablation_summary.csv")
    if os.path.exists(syn_path):
        with open(syn_path) as f:
            syn = {int(r["size"]): r for r in csv.DictReader(f)}
        L.append("  size | synthetic gain (pp)                  | "
                 "standard gain (pp)")
        L.append("       | multi-cust multi-takeoff cap3       | "
                 "multi-cust multi-takeoff cap3")
        for srow in summary_rows:
            n = srow["size"]
            s = syn.get(n)
            if not s:
                continue
            L.append(
                f"  {n:4d} | {float(s['gain_multicust_pp']):10.1f} "
                f"{float(s['gain_notakeoff_pp']):13.1f} "
                f"{float(s['gain_cap3_pp']):6.1f}       | "
                f"{srow['gain_multicust_pp']:10.1f} "
                f"{srow['gain_notakeoff_pp']:13.1f} "
                f"{srow['gain_cap3_pp']:6.1f}")
        L.append("")
        L.append("  (positive = that design choice improves the makespan; the "
                 "synthetic column comes from")
        L.append("   week07_ablation_summary.csv, i.e. the same heuristic on "
                 "the random cloud.)")
    else:
        L.append("  (synthetic summary not found; run "
                 "week07_improvement_ablation.py first)")
    L.append("")

    with open(out_raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        w.writeheader()
        w.writerows(raw_rows)
    with open(out_summary, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    text = "\n".join(L)
    with open(out_txt, "w") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[summary -> {out_summary}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
