"""
Week 6 (large-N extension) — same ground-air EVRP-TW pipeline as
week06_ground_air_evrp_tw.py, extending the scale study to N = 30, 50, 100
with multiple seeds.

Purpose (per progress_report §3.3-①): teacher suggested small/medium/large =
20/50/100; week06 covers 8/12/16/20, so this extends to 30 (medium) and 50,
then to 100 (the teacher's "large" target) to check whether the V2 advantage
holds at scale.

Compares:
  V0  truck-only (no battery)
  V1  truck EV (with recharge at stations)
  V2  ground-air collaborative EV (truck + drone)

Reuses week06's make_instance / truck_ev_route / collaborative unchanged.

NOTE on feasibility (same convention at every size): `feasible` here means
ENERGY/battery feasibility only. The greedy does NOT guarantee time-window
feasibility, so `tw_viol` counts customers served after their due time. This is
reported per size — at large N both V1 and V2 accumulate many late deliveries,
which is itself part of the scale-boundary finding (the drone can offload only a
shrinking fraction of customers, so the truck dominates and TW slips grow).
"""

import os
import sys
import time
import csv
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6

# Scale up: 30, 50 (medium) and 100 (teacher's "large" target)
SIZES = [30, 50, 100]
SEEDS = [20260820, 20260821, 20260822, 20260823, 20260824]  # 5 fresh seeds


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week06_largeN_results.csv")
    out_summary = os.path.join(res_dir, "week06_largeN_summary.csv")
    out_txt = os.path.join(res_dir, "week06_largeN_output.txt")

    L = []
    L.append("=" * 78)
    L.append("WEEK 6 LARGE-N — GROUND-AIR COLLABORATIVE EVRP-TW (N=30, 50, 100)")
    L.append("=" * 78)
    L.append(f"sizes={SIZES}  seeds={SEEDS} (total {len(SIZES)*len(SEEDS)} instances)")
    L.append(f"truck_speed={w6.V_T}  drone_speed={w6.V_D}  "
             f"drone_range={w6.R_D}  battery={w6.Q_DEFAULT}  "
             f"recharge={w6.RECHARGE}s")
    L.append("variants: V0 truck-only(no EV) | V1 truck EV | V2 ground-air collab")
    L.append("")

    rows = []
    acc = {n: {"V0": [], "V1": [], "V2": [], "off": [], "sync": [],
               "twv": [], "rechg": []} for n in SIZES}

    t0_total = time.perf_counter()
    for n in SIZES:
        L.append(f"=== size N={n} ===")
        for seed in SEEDS:
            t0 = time.perf_counter()
            inst = w6.make_instance(n, seed=seed)
            r0 = w6.run_variant(inst, "V0")
            r1 = w6.run_variant(inst, "V1")
            r2 = w6.run_variant(inst, "V2")
            el = time.perf_counter() - t0
            imp = ((r1["makespan"] - r2["makespan"]) / r1["makespan"] * 100
                   if r1["makespan"] > 0 else 0.0)
            row = {
                "size": n, "seed": seed,
                "V0_makespan": round(r0["makespan"], 1),
                "V1_makespan": round(r1["makespan"], 1),
                "V2_makespan": round(r2["makespan"], 1),
                "V2_vs_V1_pct": round(imp, 2),
                "V0_dist": round(r0["total_dist"], 1),
                "V1_dist": round(r1["total_dist"], 1),
                "V2_dist": round(r2["total_dist"], 1),
                "V0_feas": r0["feasible"],
                "V1_feas": r1["feasible"],
                "V2_feas": r2["feasible"],
                "V0_tw_viol": r0["tw_viol"],
                "V1_tw_viol": r1["tw_viol"],
                "V2_tw_viol": r2["tw_viol"],
                "V0_rechg": r0["recharges"],
                "V1_rechg": r1["recharges"],
                "V2_rechg": r2["recharges"],
                "V2_offloaded": r2["offloaded"],
                "V2_sync_rejected": r2["sync_viol"],
                "runtime_s": round(el, 3),
            }
            rows.append(row)
            acc[n]["V0"].append(r0["makespan"])
            acc[n]["V1"].append(r1["makespan"])
            acc[n]["V2"].append(r2["makespan"])
            acc[n]["off"].append(r2["offloaded"])
            acc[n]["sync"].append(r2["sync_viol"])
            acc[n]["twv"].append(r2["tw_viol"])
            acc[n]["rechg"].append(r2["recharges"])
            L.append(
                f"  seed {seed}: V0={r0['makespan']:8.1f} V1={r1['makespan']:8.1f} "
                f"V2={r2['makespan']:8.1f}  imp={imp:5.1f}%  "
                f"off={r2['offloaded']}/{n}  syncRej={r2['sync_viol']}  "
                f"twv={r2['tw_viol']}  {el:.2f}s")
        L.append("")

    # ---- aggregate ----
    L.append("=" * 78)
    L.append("AGGREGATE (mean over seeds per size)")
    L.append("=" * 78)
    summary = []
    for n in SIZES:
        v0 = acc[n]["V0"]; v1 = acc[n]["V1"]; v2 = acc[n]["V2"]
        m_imp = sum((a - b) / a * 100 for a, b in zip(v1, v2)) / len(v1)
        m_off = sum(acc[n]["off"]) / len(acc[n]["off"])
        m_sync = sum(acc[n]["sync"]) / len(acc[n]["sync"])
        m_twv = sum(acc[n]["twv"]) / len(acc[n]["twv"])
        m_rechg = sum(acc[n]["rechg"]) / len(acc[n]["rechg"])
        # compare to the week06 N=20 reference (the V2 advantage)
        srow = {
            "size": n,
            "n_instances": len(SEEDS),
            "V0_mean": round(sum(v0) / len(v0), 1),
            "V1_mean": round(sum(v1) / len(v1), 1),
            "V2_mean": round(sum(v2) / len(v2), 1),
            "V2_vs_V1_pct": round(m_imp, 1),
            "mean_offloaded": round(m_off, 1),
            "offload_rate_pct": round(m_off / n * 100, 1),
            "mean_sync_rejected": round(m_sync, 1),
            "mean_tw_viol": round(m_twv, 2),
            "mean_recharges": round(m_rechg, 2),
        }
        # keep the V2 time-window violation visible (energy feas != TW feas)
        L.append(f"  [V2 mean TW violations = {m_twv:.1f} / {n} customers]")
        summary.append(srow)
        L.append(
            f"  N={n}: V0={srow['V0_mean']:8.1f} V1={srow['V1_mean']:8.1f} "
            f"V2={srow['V2_mean']:8.1f}  V2_vs_V1={srow['V2_vs_V1_pct']:5.1f}%  "
            f"off={srow['mean_offloaded']:.1f}/{n}  twv={srow['mean_tw_viol']:.1f}")
    L.append("")
    L.append("Total runtime: %.1fs" % (time.perf_counter() - t0_total))
    L.append("=" * 78)

    # ---- write csv ----
    with open(out_raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for row in rows:
            w.writerow(row)
    with open(out_summary, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        for row in summary:
            w.writerow(row)
    text = "\n".join(L)
    with open(out_txt, "w") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[summary -> {out_summary}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
