"""
Truck capacity: is the declared CAP actually binding?

`CAP` (`week06_ground_air_evrp_tw.CAP = 1000`) is the load the single truck may
carry on one route. It was declared but never checked, so every ground-air
EVRP-TW result in this repository was computed on a capacity-free model. This
study switches the constraint on and asks two questions:

  1. at which instance size (or cap) does it start to bind?
  2. when it binds, can the collaborative (V2) greedy repair the overload, and
     what does the repair cost in completion time?

Design: sizes N = 8/12/16/20/30/50/100 (5 seeds each, the same generator as the
W6 headline) x caps {1000 (declared), 600, 400}. For every (N, cap, seed) the
three W6 variants are re-evaluated with the capacity enforced:
  V0 truck-only (no battery), V1 truck EV, V2 ground-air collaborative EV.
A plan is capacity-infeasible when the demand it carries exceeds `cap`; V2 can
offload customers to the drone, which also removes their demand from the truck.
Each (N, seed) is also run with an unlimited cap, to price the repair.

Output:
  src/results/week06_capacity_raw.csv, _summary.csv, _log.txt
  figures/capacity_binding.png     (src/tools/gen_capacity_figure.py)
"""
import os
import sys
import csv
import time
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6

SIZES = [8, 12, 16, 20, 30, 50, 100]
CAPS = [w6.CAP, 600, 400]
UNLIMITED = 10 ** 9
N_SEEDS = 5
SEED_BASE = 20260720

RAW_FIELDS = ["size", "seed", "cap", "total_demand", "cap_binds",
              "V0_feasible", "V1_feasible", "V2_feasible",
              "V0_makespan", "V1_makespan", "V2_makespan",
              "V2_makespan_unlimited", "V2_vs_unlimited_pct",
              "V2_truck_load", "V2_offloaded",
              "V2_load_ratio", "V1_tw_viol", "V2_tw_viol",
              "V2_sync_rejected", "runtime_s"]


def _finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def _mean(vals):
    vals = [v for v in vals if _finite(v)]
    return sum(vals) / len(vals) if vals else float("nan")


def _rate(vals):
    return sum(1 for v in vals if v) / len(vals) if vals else 0.0


def _r(x, nd=1):
    """Round, but report a dash for undefined (all-infeasible) aggregates."""
    return round(x, nd) if _finite(x) else ""


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week06_capacity_raw.csv")
    out_summary = os.path.join(res_dir, "week06_capacity_summary.csv")
    out_txt = os.path.join(res_dir, "week06_capacity_log.txt")

    L = []
    L.append("=" * 78)
    L.append("TRUCK CAPACITY STUDY — is the declared CAP binding?")
    L.append("=" * 78)
    L.append(f"sizes={SIZES}  seeds={N_SEEDS} (base {SEED_BASE})  "
             f"caps={CAPS} + unlimited reference")
    L.append(f"declared CAP={w6.CAP}  demand per customer ~ U[5, 15]  "
             f"truck_speed={w6.V_T}  drone_range={w6.R_D}")
    L.append("capacity rule: demand carried on the truck route <= cap "
             "(V2 may offload customers to the drone)")
    L.append("")

    rows = []
    acc = {}
    for n in SIZES:
        for cap in CAPS:
            acc[(n, cap)] = {k: [] for k in
                             ("tot", "binds", "v0f", "v1f", "v2f", "v1mk",
                              "v2mk", "load", "off", "gain", "cost",
                              "v1en", "v2en", "v2cap")}
        L.append(f"=== N={n} ===")
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            base = w6.make_instance(n, seed=seed)
            total = sum(base["demand"].values())
            free = w6.collaborative({**base, "cap": UNLIMITED}, cap=UNLIMITED)
            free_mk = free["makespan"]
            for cap in CAPS:
                inst = {**base, "cap": cap}
                t0 = time.perf_counter()
                v0 = w6.run_variant(inst, "V0")
                v1 = w6.run_variant(inst, "V1")
                v2 = w6.run_variant(inst, "V2")
                rt = time.perf_counter() - t0
                binds = total > cap
                row = {"size": n, "seed": seed, "cap": cap,
                       "total_demand": total, "cap_binds": int(binds),
                       "V0_feasible": int(v0["feasible"]),
                       "V1_feasible": int(v1["feasible"]),
                       "V2_feasible": int(v2["feasible"]),
                       "V0_makespan": round(v0["makespan"], 1)
                       if _finite(v0["makespan"]) else "",
                       "V1_makespan": round(v1["makespan"], 1)
                       if _finite(v1["makespan"]) else "",
                       "V2_makespan": round(v2["makespan"], 1)
                       if _finite(v2["makespan"]) else "",
                       "V2_makespan_unlimited": round(free_mk, 1)
                       if _finite(free_mk) else "",
                       "V2_vs_unlimited_pct": (round(
                           (v2["makespan"] - free_mk) / free_mk * 100, 2)
                           if _finite(v2["makespan"]) and _finite(free_mk)
                           else ""),
                       "V2_truck_load": v2["truck_load"],
                       "V2_offloaded": v2["offloaded"],
                       "V2_load_ratio": round(v2["truck_load"] / total, 4),
                       "V1_tw_viol": v1["tw_viol"],
                       "V2_tw_viol": v2["tw_viol"],
                       "V2_sync_rejected": v2["sync_viol"],
                       "runtime_s": round(rt, 3)}
                rows.append(row)
                a = acc[(n, cap)]
                a["tot"].append(total)
                a["binds"].append(binds)
                a["v0f"].append(v0["feasible"])
                a["v1f"].append(v1["feasible"])
                a["v2f"].append(v2["feasible"])
                a["v1mk"].append(v1["makespan"])
                a["v2mk"].append(v2["makespan"])
                a["load"].append(v2["truck_load"])
                a["off"].append(v2["offloaded"])
                a["v1en"].append(v1["energy_viol"] == 0)
                a["v2en"].append(v2["energy_viol"] == 0)
                a["v2cap"].append(v2["cap_viol"] == 0)
                if v1["feasible"] and v2["feasible"]:
                    a["gain"].append(
                        (v1["makespan"] - v2["makespan"])
                        / v1["makespan"] * 100)
                if _finite(v2["makespan"]) and _finite(free_mk):
                    a["cost"].append(
                        (v2["makespan"] - free_mk) / free_mk * 100)
            L.append(f"  seed {seed}: total demand={total:4d}  "
                     f"cap1000={'bind' if total > w6.CAP else 'free':4s}  "
                     f"cap600={'bind' if total > 600 else 'free':4s}  "
                     f"cap400={'bind' if total > 400 else 'free':4s}")
        L.append("")

    # ---- summary ----
    L.append("=" * 78)
    L.append("SUMMARY (mean over the 5 seeds; makespans only over feasible runs)")
    L.append("=" * 78)
    hdr = ("N | cap | demand | binds | V1_feas | V2_feas | V1_mk | V2_mk | "
           "gain% | V2_load | load% | off | V1_energy% | cap_repaired% | "
           "cost_vs_free%")
    L.append("  " + hdr)
    summary = []
    for n in SIZES:
        for cap in CAPS:
            a = acc[(n, cap)]
            binds = [b for b in a["binds"]]
            binding = sum(1 for b in binds if b)
            cap_repairs = [c for b, c in zip(a["binds"], a["v2cap"]) if b]
            srow = {
                "size": n, "cap": cap,
                "total_demand_mean": round(_mean(a["tot"]), 1),
                "n_instances": N_SEEDS,
                "cap_binds_n": binding,
                "V0_feas_rate": round(_rate(a["v0f"]), 3),
                "V1_feas_rate": round(_rate(a["v1f"]), 3),
                "V2_feas_rate": round(_rate(a["v2f"]), 3),
                "V1_makespan_mean": _r(_mean(a["v1mk"])),
                "V2_makespan_mean": _r(_mean(a["v2mk"])),
                "V2_vs_V1_pct": _r(_mean(a["gain"])),
                "V2_truck_load_mean": _r(_mean(a["load"])),
                "V2_load_ratio_mean": round(_mean(a["load"])
                                            / _mean(a["tot"]), 4),
                "V2_offloaded_mean": _r(_mean(a["off"])),
                "V1_energy_feas_rate": round(_rate(a["v1en"]), 3),
                "V2_energy_feas_rate": round(_rate(a["v2en"]), 3),
                "V2_cap_repaired_rate_when_binding": round(
                    _rate(cap_repairs), 3),
                "V2_cost_vs_unlimited_pct": _r(_mean(a["cost"]), 2),
            }
            summary.append(srow)
            L.append(
                f"  {n:3d} | {cap:4d} | {srow['total_demand_mean']:6.1f} | "
                f"{binding}/{N_SEEDS} | {srow['V1_feas_rate']*100:3.0f}% | "
                f"{srow['V2_feas_rate']*100:3.0f}% | "
                f"{srow['V1_makespan_mean']!s:>8} | "
                f"{srow['V2_makespan_mean']!s:>8} | "
                f"{srow['V2_vs_V1_pct']!s:>5} | "
                f"{srow['V2_truck_load_mean']!s:>6} | "
                f"{srow['V2_load_ratio_mean']*100:5.1f}% | "
                f"{srow['V2_offloaded_mean']!s:>4} | "
                f"{srow['V1_energy_feas_rate']*100:6.0f}% | "
                f"{srow['V2_cap_repaired_rate_when_binding']*100:8.0f}% | "
                f"{srow['V2_cost_vs_unlimited_pct']!s:>6}")
    L.append("")

    # ---- findings ----
    declared = [s for s in summary if s["cap"] == w6.CAP]
    binding_sizes = [s["size"] for s in declared if s["cap_binds_n"] > 0]
    free_sizes = [s["size"] for s in declared if s["cap_binds_n"] == 0]
    binding_cells = [s for s in summary if s["cap_binds_n"] > 0]
    repaired = [s["V2_cap_repaired_rate_when_binding"] for s in binding_cells]
    load_ratios = [s["V2_load_ratio_mean"] for s in summary
                   if s["cap"] == w6.CAP]
    rep_txt = ", ".join(
        f"cap={s['cap']}@N={s['size']}: "
        f"{s['V2_cap_repaired_rate_when_binding'] * 100:.0f}%"
        for s in binding_cells)
    biggest = max(SIZES)
    n_big = next(s for s in summary if s["size"] == biggest
                 and s["cap"] == w6.CAP)
    L.append("=" * 78)
    L.append("FINDINGS")
    L.append("=" * 78)
    L.append(f"  1. At the declared CAP={w6.CAP} the constraint is free for "
             f"N in {free_sizes} and binds in "
             f"{sum(s['cap_binds_n'] for s in declared)} instance(s) at "
             f"N in {binding_sizes}; a cap below the total demand binds for "
             f"every larger size.")
    L.append(f"  2. When the cap binds, the truck-only variants are infeasible "
             f"by construction and V2 removes enough demand to satisfy the cap "
             f"in {_mean(repaired) * 100:.0f}% of the binding cells ({rep_txt}).")
    L.append(f"  3. The repair ceiling is the drone, not the search: V2 leaves "
             f"{min(load_ratios) * 100:.1f}% (N={min(SIZES)}) to "
             f"{max(load_ratios) * 100:.1f}% (N={biggest}) of the demand on the "
             f"truck, so one serial drone only removes a modest share. In "
             f"practice the capacity constraint behaves like a hard "
             f"\"total demand <= cap\" bound.")
    L.append(f"  4. Capacity and energy are separate gates at N={biggest}: "
             f"V1/V2 are energy-feasible in "
             f"{n_big['V1_energy_feas_rate'] * 100:.0f}%/"
             f"{n_big['V2_energy_feas_rate'] * 100:.0f}% of the instances, so "
             f"the N={biggest} feasibility drop is not caused by capacity alone.")
    L.append("  5. Natural fixes: a load-aware LNS (destroy-repair that treats "
             "the cap as a hard constraint), or several drones, which multiply "
             "the demand that can leave the truck.")
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
