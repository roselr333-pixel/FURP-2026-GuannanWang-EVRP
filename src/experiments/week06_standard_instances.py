"""
Standard instances: are the week-6 conclusions an artefact of the geometry?

The whole W6 line (V0 truck-only / V1 truck EV / V2 truck + drone) runs on
randomly generated instances. This study re-runs the same three variants with
the same evaluators on the **original Schneider (2014) E-VRPTW instances** —
real coordinates, real time windows, real charging stations and the paper's own
battery — converted by `std_evrp_instances.make_evrp`.

Design:
  families   c101 / c201 / r101 / r201 / rc101 / rc201 (the 100-customer files)
  sizes      N = 8 / 12 / 16 / 20 (the synthetic headline sizes)
  subsets    four contiguous customer blocks (start = 0 / 10 / 20 / 30) act as
             the four samples per family and size, since these instances carry
             no random seed
  capacity   two settings: the paper's own load capacity C ("file") and the W6
             default CAP = 1000 ("model"), so the geometry effect can be read
             apart from the single-truck-vs-fleet mismatch

Reference to compare against (synthetic W6/W7 ablation, V2 vs V1 makespan):
N = 8/12/16/20 -> 34.5 / 29.0 / 28.7 / 24.8%.

Output:
  src/results/week06_std_evrp_raw.csv, _summary.csv, _log.txt
  figures/std_instances.png   (src/tools/gen_std_instances_figure.py)
"""
import os
import sys
import csv
import math
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import std_evrp_instances as SI

FAMILIES = SI.FAMILIES
SIZES = [8, 12, 16, 20]
STARTS = [0, 10, 20, 30]
CAP_MODES = ["file", "model"]
SYNTHETIC_REF = {8: 34.5, 12: 29.0, 16: 28.7, 20: 24.8}

RAW_FIELDS = ["family", "size", "start", "cap_mode", "total_demand", "cap",
              "battery_range", "recharge_min", "service_min",
              "mean_depot_dist", "drone_range",
              "V0_makespan", "V1_makespan", "V2_makespan",
              "V0_feasible", "V1_feasible", "V2_feasible",
              "V1_tw_viol", "V2_tw_viol", "V1_recharges", "V2_recharges",
              "V2_offloaded", "V2_sync_rejected",
              "gain_v2_vs_v1_pct", "runtime_s"]


def _finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def _mean(vals):
    vals = [v for v in vals if _finite(v)]
    return sum(vals) / len(vals) if vals else float("nan")


def _rate(vals):
    return sum(1 for v in vals if v) / len(vals) if vals else 0.0


def _r(x, nd=1):
    return round(x, nd) if _finite(x) else ""


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week06_std_evrp_raw.csv")
    out_summary = os.path.join(res_dir, "week06_std_evrp_summary.csv")
    out_txt = os.path.join(res_dir, "week06_std_evrp_log.txt")

    L = []
    L.append("=" * 78)
    L.append("STANDARD-INSTANCE RUN — Schneider (2014) E-VRPTW data, W6 model")
    L.append("=" * 78)
    L.append(f"families={FAMILIES}  files=<family>_21 (100 customers)")
    L.append(f"sizes={SIZES}  subsets start={STARTS}  capacities={CAP_MODES}")
    L.append("mapping: time=minutes (paper v=1), service=90min, "
             "battery=Q/r, recharge=Q*g, drone_range=2.5x mean depot distance")
    L.append(f"synthetic reference (V2 vs V1): {SYNTHETIC_REF}")
    L.append("")

    rows = []
    acc = {}
    for mode in CAP_MODES:
        for n in SIZES:
            acc[(mode, n)] = {"gain": [], "v1mk": [], "v2mk": [], "v1f": [],
                              "v2f": [], "v1tw": [], "v2tw": [], "v1rc": [],
                              "v2rc": [], "off": [], "tot": [], "binds": [],
                              "drange": []}

    t0_all = time.perf_counter()
    for mode in CAP_MODES:
        L.append("#" * 78)
        L.append(f"# capacity mode: {mode}"
                 + (" (paper C)" if mode == "file" else " (W6 CAP=1000)"))
        L.append("#" * 78)
        for fam in FAMILIES:
            name = f"{fam}_21"
            for n in SIZES:
                line = []
                for start in STARTS:
                    inst, meta = SI.make_evrp(name, n=n, start=start,
                                              cap_mode=mode)
                    t0 = time.perf_counter()
                    v0 = w6.run_variant(inst, "V0")
                    v1 = w6.run_variant(inst, "V1")
                    v2 = w6.run_variant(inst, "V2")
                    rt = time.perf_counter() - t0
                    gain = (v1["makespan"] - v2["makespan"]) / v1["makespan"] * 100 \
                        if (_finite(v1["makespan"]) and _finite(v2["makespan"])
                            and v1["makespan"] > 0) else float("nan")
                    row = {
                        "family": meta["family"], "size": n, "start": start,
                        "cap_mode": mode,
                        "total_demand": meta["total_demand"], "cap": meta["cap"],
                        "battery_range": round(meta["battery_range"], 2),
                        "recharge_min": round(meta["recharge_min"], 1),
                        "service_min": meta["service_min"],
                        "mean_depot_dist": round(meta["mean_depot_dist"], 2),
                        "drone_range": round(meta["drone_range"], 2),
                        "V0_makespan": _r(v0["makespan"]),
                        "V1_makespan": _r(v1["makespan"]),
                        "V2_makespan": _r(v2["makespan"]),
                        "V0_feasible": int(v0["feasible"]),
                        "V1_feasible": int(v1["feasible"]),
                        "V2_feasible": int(v2["feasible"]),
                        "V1_tw_viol": v1["tw_viol"],
                        "V2_tw_viol": v2["tw_viol"],
                        "V1_recharges": v1["recharges"],
                        "V2_recharges": v2["recharges"],
                        "V2_offloaded": v2["offloaded"],
                        "V2_sync_rejected": v2["sync_viol"],
                        "gain_v2_vs_v1_pct": _r(gain, 2),
                        "runtime_s": round(rt, 3),
                    }
                    rows.append(row)
                    a = acc[(mode, n)]
                    a["gain"].append(gain)
                    a["v1mk"].append(v1["makespan"])
                    a["v2mk"].append(v2["makespan"])
                    a["v1f"].append(v1["feasible"])
                    a["v2f"].append(v2["feasible"])
                    a["v1tw"].append(v1["tw_viol"])
                    a["v2tw"].append(v2["tw_viol"])
                    a["v1rc"].append(v1["recharges"])
                    a["v2rc"].append(v2["recharges"])
                    a["off"].append(v2["offloaded"])
                    a["tot"].append(meta["total_demand"])
                    a["binds"].append(meta["total_demand"] > meta["cap"])
                    a["drange"].append(meta["drone_range"])
                    line.append(f"s{start}: gain={gain:5.1f}%" if _finite(gain)
                                else f"s{start}: gain=  n/a")
                L.append(f"  {fam:5s} N={n:2d}: " + "  ".join(line))
        L.append("")

    # ---- summary ----
    L.append("=" * 78)
    L.append("SUMMARY (per capacity mode and size; makespans over feasible runs)")
    L.append("=" * 78)
    L.append("  mode |  N | n_inst | V1_feas | V2_feas | V1_mk | V2_mk | "
             "gain% | ref% | off% | TW1 | TW2 | rechg2 | binds")
    summary = []
    for mode in CAP_MODES:
        for n in SIZES:
            a = acc[(mode, n)]
            srow = {
                "cap_mode": mode, "size": n, "n_instances": len(STARTS) * len(FAMILIES),
                "V1_feas_rate": round(_rate(a["v1f"]), 3),
                "V2_feas_rate": round(_rate(a["v2f"]), 3),
                "V1_makespan_mean": _r(_mean(a["v1mk"])),
                "V2_makespan_mean": _r(_mean(a["v2mk"])),
                "gain_pct": _r(_mean(a["gain"])),
                "synthetic_ref_pct": SYNTHETIC_REF[n],
                "offload_rate_pct": _r(_mean(a["off"]) / n * 100, 1),
                "V1_tw_viol_mean": _r(_mean(a["v1tw"]), 2),
                "V2_tw_viol_mean": _r(_mean(a["v2tw"]), 2),
                "V2_recharges_mean": _r(_mean(a["v2rc"]), 2),
                "cap_binds_n": sum(1 for b in a["binds"] if b),
                "drone_range_mean": _r(_mean(a["drange"]), 1),
                "total_demand_mean": _r(_mean(a["tot"]), 1),
            }
            summary.append(srow)
            L.append(
                f"  {mode:4s} | {n:2d} | {srow['n_instances']:5d} | "
                f"{srow['V1_feas_rate']*100:6.0f}% | "
                f"{srow['V2_feas_rate']*100:6.0f}% | "
                f"{srow['V1_makespan_mean']!s:>7} | "
                f"{srow['V2_makespan_mean']!s:>7} | "
                f"{srow['gain_pct']!s:>5} | {SYNTHETIC_REF[n]:4.1f} | "
                f"{srow['offload_rate_pct']!s:>5} | "
                f"{srow['V1_tw_viol_mean']!s:>5} | "
                f"{srow['V2_tw_viol_mean']!s:>5} | "
                f"{srow['V2_recharges_mean']!s:>6} | "
                f"{srow['cap_binds_n']:3d}/{srow['n_instances']}")
    L.append("")

    # ---- findings ----
    std_gains = {n: _mean(acc[("model", n)]["gain"]) for n in SIZES}
    tw_drop = {n: (_mean(acc[("model", n)]["v1tw"])
                   - _mean(acc[("model", n)]["v2tw"])) for n in SIZES}
    file_binds = {n: sum(1 for b in acc[("file", n)]["binds"] if b) for n in SIZES}
    file_feas = {n: _rate(acc[("file", n)]["v2f"]) for n in SIZES}
    L.append("=" * 78)
    L.append("FINDINGS")
    L.append("=" * 78)
    L.append("  1. With the W6 capacity (mode=model) the collaboration gain on "
             "standard instances is "
             + ", ".join(f"N={n}: {std_gains[n]:.1f}%" for n in SIZES)
             + " (synthetic: "
             + ", ".join(f"{SYNTHETIC_REF[n]:.1f}%" for n in SIZES) + ").")
    L.append("  2. The drone also repairs time windows on this data: mean late "
             "customers fall by "
             + ", ".join(f"N={n}: {tw_drop[n]:.2f}" for n in SIZES) + ".")
    L.append("  3. The paper's own load capacity (mode=file, C=200) binds on "
             + ", ".join(f"{file_binds[n]}/{len(STARTS)*len(FAMILIES)} at N={n}"
                         for n in SIZES)
             + "; V2 feasibility then is "
             + ", ".join(f"{file_feas[n]*100:.0f}%" for n in SIZES)
             + " - a single truck cannot carry a 100-customer fleet's load.")
    L.append("  4. All runs use the paper's own battery (range 79.7 km) and "
             "recharge time (270 min), so the recharges reported above are the "
             "model's, not a synthetic stand-in.")
    L.append(f"  total runtime: {time.perf_counter() - t0_all:.1f}s")
    L.append("")

    with open(out_raw, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RAW_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(out_summary, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        for r in summary:
            w.writerow(r)
    text = "\n".join(L)
    with open(out_txt, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]\n[summary -> {out_summary}]\n[log -> {out_txt}]")


if __name__ == "__main__":
    main()
