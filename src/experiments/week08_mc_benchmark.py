"""
Benchmark my truck-drone method on the ORIGINAL Murray & Chu (2015) FSTSP
instances (src/instances/murray_chu_2015/), and compare against the objective
values distributed with those instances (FSTSP_OFV.csv).

Two knobs are swept so the comparison can be read two ways:
  max_cust = 1 : exactly M&C's FSTSP (one customer per sortie) -> fair
                 comparison against the published objective values
  max_cust = 2 : my extension (a sortie may serve two customers)
  K            : number of drones (1/2/3)

Caveats that are reported, not hidden: the distributed files contain no drone
endurance, so endurance is unlimited here (the longest flight in each solution
is reported); and there are no service times, so service = 0.

Run:
  python src/experiments/week08_mc_benchmark.py
"""

import os
import sys
import csv
import time
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fstsp_mc as M
import sysinfo as SI

MAX_CUSTS = [1, 2]
DRONES = [1, 2, 3]
ITERS = 200
SEED = 20260720


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    os.makedirs(res, exist_ok=True)
    out_raw = os.path.join(res, "week08_mc_benchmark_raw.csv")
    out_txt = os.path.join(res, "week08_mc_benchmark_log.txt")

    rows = []
    for name in M.list_instances():
        t0 = time.perf_counter()
        inst = M.load_mc(name)
        tsp = M.mc_tsp_opt(inst, inst["tau"])
        row = {"instance": name, "uav_speed": inst["uav_speed_declared"],
               "n_customers": inst["n"], "truck_only_tsp": round(tsp, 2),
               "ofv": (round(inst["ofv"], 2) if inst["ofv"] else "")}
        for mc in MAX_CUSTS:
            for K in DRONES:
                gr, gt = M.mc_greedy(inst, K=K, max_cust=mc)
                g = M.mc_simulate(inst, gr, gt, inst["tau"],
                                  inst["tauprime"], K)
                lr, lt, l = M.mc_lns(inst, K=K, max_cust=mc, iters=ITERS,
                                     seed=SEED)
                tag = f"c{mc}K{K}"
                row[f"{tag}_greedy"] = round(g, 2)
                row[f"{tag}_lns"] = round(l, 2)
                row[f"{tag}_maxflight"] = round(
                    M._max_flight(inst, inst["tauprime"], lt), 2)
                row[f"{tag}_lns_vs_tsp_pct"] = round(
                    (tsp - l) / tsp * 100, 1)
                if inst["ofv"]:
                    row[f"{tag}_lns_over_ofv"] = round(l / inst["ofv"], 3)
        row["runtime_s"] = round(time.perf_counter() - t0, 2)
        rows.append(row)
        print(f"  {name}  ({row['runtime_s']:.2f}s)")

    # some instances carry a published OFV and some do not, so take the union
    # of all keys as the header
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(out_raw, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    L = []
    L.append("=" * 78)
    L.append("My method on the ORIGINAL Murray & Chu (2015) FSTSP instances")
    L.append("=" * 78)
    L.append(f"instances: {len(rows)}   max_cust {MAX_CUSTS}   K {DRONES}   "
             f"LNS iters {ITERS}")
    L.append("truck = tau matrix, UAV = tauprime matrix "
             "(calibrated on all 36 instances)")
    L.extend(SI.env_lines())
    L.append(f"total wall-clock: {sum(r['runtime_s'] for r in rows):.1f}s "
             f"over {len(rows)} instances "
             f"(mean {statistics.mean([r['runtime_s'] for r in rows]):.2f}s/instance)")
    L.append("")
    L.append("mean over instances:")
    hdr = f"  {'config':10s} {'LNS':>8s} {'vs truck TSP':>13s}"
    ofv_rows = [r for r in rows if r["ofv"] != ""]
    if ofv_rows:
        hdr += f" {'LNS/OFV':>9s}   (n={len(ofv_rows)} with published OFV)"
    L.append(hdr)
    for mc in MAX_CUSTS:
        for K in DRONES:
            tag = f"c{mc}K{K}"
            lns = [r[f"{tag}_lns"] for r in rows]
            pct = [r[f"{tag}_lns_vs_tsp_pct"] for r in rows]
            line = f"  {tag:10s} {statistics.mean(lns):8.2f} " \
                   f"{statistics.mean(pct):12.1f}%"
            if ofv_rows:
                line += f" {statistics.mean([r[f'{tag}_lns_over_ofv'] for r in ofv_rows]):9.3f}"
            L.append(line)
    L.append("")
    L.append("max drone flight time in the LNS solutions (no endurance is given")
    L.append("in the distributed files, so endurance is unlimited here):")
    for mc in MAX_CUSTS:
        for K in DRONES:
            tag = f"c{mc}K{K}"
            L.append(f"  {tag:10s} mean {statistics.mean([r[f'{tag}_maxflight'] for r in rows]):6.2f}  "
                     f"max {max(r[f'{tag}_maxflight'] for r in rows):6.2f}")
    L.append("")
    L.append("Reading: LNS/OFV < 1 means better than the objective value")
    L.append("published with the instances. c1 = M&C's own FSTSP (one customer")
    L.append("per sortie); c2 = my multi-customer extension.")

    text = "\n".join(L)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print()
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
