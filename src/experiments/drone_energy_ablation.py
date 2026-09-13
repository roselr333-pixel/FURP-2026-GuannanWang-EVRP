"""
Core ablation under the drone energy / payload model.

The main line limits the drone with a range constant only, so the drone is never
"electric". drone_energy.py adds a payload capacity and an energy budget whose
consumption rate grows with the load on board. This runner asks the question that
matters for the project's headline attribution: once the drone has to carry the
energy for its payload, does the multi-customer advantage survive?

It runs the same four configurations plus the published Murray & Chu (2015)
insertion heuristic, on the same two instance sets as the earlier ablations
(synthetic 10 seeds x N=8/12/16/20, and 48 standard Solomon instances), at three
settings of the payload coefficient BETA:

  BETA = 0.00   the energy budget is exactly the old range limit (validation row)
  BETA = 0.02   default: consumption grows 2% per demand unit per distance unit
  BETA = 0.04   heavier payload penalty

Everything else is fixed: same greedy loop, same truck-waiting / serial-drone
evaluator, same seeds. The published heuristic is not energy-aware -- its plans
are simply re-evaluated, and its feasibility rate under the model is reported.

Run:
  python src/experiments/drone_energy_ablation.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import fstsp_instances as fi
import drone_energy as DE
import sysinfo as SI

BETAS = [0.0, 0.02, 0.04]
SIZES = [8, 12, 16, 20]
N_SEEDS = 10
SEED_BASE = 20260720
FAMILIES = fi.FAMILIES
WINDOWS = [0, 1, 2]

CONFIGS = {
    "published": lambda inst, kw: f7.fstsp_insertion(inst),
    "cap1": lambda inst, kw: DE.greedy(inst, max_cust=1, **kw),
    "v2": lambda inst, kw: DE.greedy(inst, max_cust=2, **kw),
    "notakeoff": lambda inst, kw: DE.greedy(inst, max_cust=2,
                                            multi_takeoff=False, **kw),
    "cap3": lambda inst, kw: DE.greedy(inst, max_cust=3, **kw),
}


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def instances():
    out = []
    for n in SIZES:
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            out.append(("synthetic", n, f"synth-n{n}-s{seed}",
                        w6.make_instance(n, seed=seed)))
    for name in FAMILIES:
        for n in SIZES:
            for win in WINDOWS:
                out.append(("standard", n, f"{name}-n{n}-w{win}",
                            fi.make_solomon_fstsp(name, n, start=win * n)))
    return out


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "drone_energy_raw.csv")
    out_summary = os.path.join(res_dir, "drone_energy_summary.csv")
    out_txt = os.path.join(res_dir, "drone_energy_log.txt")

    insts = instances()
    L = []
    L.append("=" * 78)
    L.append("Core ablation under the drone energy / payload model")
    L.append("=" * 78)
    L.append(f"instances: synthetic {N_SEEDS} seeds x {SIZES} = "
             f"{N_SEEDS * len(SIZES)}; standard {len(FAMILIES)} families x "
             f"{len(WINDOWS)} windows x {SIZES} = "
             f"{len(FAMILIES) * len(WINDOWS) * len(SIZES)}")
    L.append(f"BETA values: {BETAS}   ALPHA={DE.ALPHA}  E_D={DE.E_D}  "
             f"P_MAX={DE.P_MAX}")
    L.append(f"reference: range-only model is R_D={w6.R_D} (BETA=0, E_D=R_D)")
    L.extend(SI.env_lines())
    L.append("")

    raw_rows = []
    summary_rows = []
    for beta in BETAS:
        kw = {"beta": beta}
        L.append("=" * 78)
        L.append(f"BETA = {beta}")
        L.append("=" * 78)
        for iset in ("synthetic", "standard"):
            for n in SIZES:
                sub = [x for x in insts if x[0] == iset and x[1] == n]
                truck = []
                for _, _, tag, inst in sub:
                    route = [0] + w6.nn_order(inst,
                                              list(inst["customers"].keys()))                         + [0]
                    truck.append(DE.makespan(inst, route, [], **kw))
                srow = {"instance_set": iset, "beta": beta, "size": n,
                        "n_instances": len(sub),
                        "truck_only_makespan": round(_mean(truck), 1)}
                for tag, _, _, inst in sub:
                    row = {"instance_set": iset, "beta": beta, "size": n,
                           "instance": tag}
                    for cname, fn in CONFIGS.items():
                        t0 = time.perf_counter()
                        route, trips, off = fn(inst, kw)
                        rt = time.perf_counter() - t0
                        mk = DE.makespan(inst, route, trips, **kw)
                        row[f"{cname}_makespan"] = ("" if mk == DE.INF
                                                    else round(mk, 1))
                        row[f"{cname}_feasible"] = (mk != DE.INF)
                        row[f"{cname}_offloaded"] = len(off)
                        row[f"{cname}_trips"] = len(trips)
                        row[f"{cname}_runtime_s"] = round(rt, 4)
                    raw_rows.append(row)
                for cname in CONFIGS:
                    vals = [r[f"{cname}_makespan"] for r in raw_rows
                            if r["instance_set"] == iset and r["beta"] == beta
                            and r["size"] == n]
                    ok = [r[f"{cname}_feasible"] for r in raw_rows
                          if r["instance_set"] == iset and r["beta"] == beta
                          and r["size"] == n]
                    finite = [v for v in vals if v != ""]
                    imp = _mean([(a - b) / a * 100
                                 for a, b in zip(truck, vals) if b != ""])
                    srow[f"{cname}_makespan"] = round(_mean(finite), 1) \
                        if finite else ""
                    srow[f"{cname}_imp_vs_truck_pct"] = round(imp, 1)
                    srow[f"{cname}_feas_rate"] = round(_mean(
                        [1.0 if x else 0.0 for x in ok]), 3)
                    srow[f"{cname}_offloaded"] = round(_mean(
                        [r[f"{cname}_offloaded"] for r in raw_rows
                         if r["instance_set"] == iset and r["beta"] == beta
                         and r["size"] == n]), 1)
                impc = lambda c: srow[f"{c}_imp_vs_truck_pct"]  # noqa: E731
                srow["gain_multicust_pp"] = round(impc("v2") - impc("cap1"), 1)
                srow["gain_notakeoff_pp"] = round(
                    impc("v2") - impc("notakeoff"), 1)
                srow["gain_cap3_pp"] = round(impc("cap3") - impc("v2"), 1)
                summary_rows.append(srow)
                L.append(
                    f"  {iset:9s} N={n:2d}: truck={srow['truck_only_makespan']:7.1f}"
                    f"  pub={srow['published_imp_vs_truck_pct']:5.1f}%"
                    f"(ok {srow['published_feas_rate']:.2f})"
                    f"  cap1={srow['cap1_imp_vs_truck_pct']:5.1f}%"
                    f"  v2={srow['v2_imp_vs_truck_pct']:5.1f}%"
                    f"  notakeoff={srow['notakeoff_imp_vs_truck_pct']:5.1f}%"
                    f"  cap3={srow['cap3_imp_vs_truck_pct']:5.1f}%"
                    f"   multi-cust {srow['gain_multicust_pp']:+}pp"
                    f"  takeoff {srow['gain_notakeoff_pp']:+}pp"
                    f"  cap3 {srow['gain_cap3_pp']:+}pp")
        L.append("")

    # ---- headline: the multi-customer gain as the payload penalty grows ----
    L.append("=" * 78)
    L.append("MULTI-CUSTOMER GAIN vs PAYLOAD COEFFICIENT (pp, mean over sizes)")
    L.append("=" * 78)
    L.append("  instance set | " + " | ".join(f"BETA={b}" for b in BETAS))
    for iset in ("synthetic", "standard"):
        cells = []
        for beta in BETAS:
            sub = [r for r in summary_rows
                   if r["instance_set"] == iset and r["beta"] == beta]
            cells.append(f"{_mean([r['gain_multicust_pp'] for r in sub]):+6.1f}")
        L.append(f"  {iset:12s} | " + " | ".join(cells))
    L.append("")
    L.append("  offload rate of the v2 configuration (customers/instance):")
    for iset in ("synthetic", "standard"):
        cells = []
        for beta in BETAS:
            sub = [r for r in summary_rows
                   if r["instance_set"] == iset and r["beta"] == beta]
            cells.append(f"{_mean([r['v2_offloaded'] for r in sub]):6.1f}")
        L.append(f"  {iset:12s} | " + " | ".join(cells))
    L.append("")

    with open(out_raw, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        w.writeheader()
        w.writerows(raw_rows)
    with open(out_summary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    text = "\n".join(L)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[summary -> {out_summary}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
