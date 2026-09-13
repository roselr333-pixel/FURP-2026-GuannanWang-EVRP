"""
Drone energy and payload on the main line (V3 and W8).

`drone_energy.py` gives the drone a payload capacity `P_MAX` and an energy
budget `E_D` whose consumption grows with the load still on board, but that
model lived in its own runner on the FSTSP evaluator, which has no truck battery
and no time windows. This module puts the same two gates on the settings the main
line actually uses:

  V3  electric truck + drone + charging stations + time windows
      (`v3_ev_collab.ev_collab_k`, K = 1/2/3 drones)
  W8  the K parallel serial drones of `week08_multidrone`, on the FSTSP
      evaluator (no battery, no time windows)

Both are swept over `BETA = 0.00` and `BETA = 0.02`, with `E_D = 160` and
`P_MAX = 30`. `BETA = 0` makes the energy budget exactly the range constant, so
that row is a control: its numbers must reproduce the committed range-only runs
(the log prints the difference against `v3_ev_collab_summary.csv` and
`week08_multidrone_summary.csv`).

Run:
  python src/experiments/drone_energy_mainline.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week08_lns as L
import week08_multidrone as M
import v3_ev_collab as V3
import drone_energy as DE
import sysinfo as SI

HERE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

BETAS = [0.0, 0.02]
E_D = DE.E_D
P_MAX = DE.P_MAX
SIZES = [8, 12, 16, 20]
N_SEEDS = 10
SEED_BASE = 20260720
K_DRONES = [1, 2, 3]
CONFIGS = ["greedy", "K1", "K2", "K3"]
INF = float("inf")


def kw_of(beta):
    """Evaluator keyword arguments for one payload coefficient."""
    return {"alpha": DE.ALPHA, "beta": beta, "ed": E_D, "p_max": P_MAX}


def _num(mk):
    """CSV cell for a makespan: blank when the plan is infeasible."""
    return "" if mk == INF else round(mk, 1)


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def _row(beta, n, seed):
    return {"beta": beta, "size": n, "seed": seed}


def v3_rows():
    """V3: electric truck + charging + time windows, K = 1/2/3 drones."""
    rows = []
    for beta in BETAS:
        kw = kw_of(beta)
        for n in SIZES:
            for s in range(N_SEEDS):
                seed = SEED_BASE + s
                inst = w6.make_instance(n, seed=seed)
                v1 = w6.truck_ev_route(inst, list(inst["customers"].keys()),
                                       allow_recharge=True)
                gf = (lambda kw: (lambda inst: V3.v3_greedy(inst, **kw)))(kw)
                gr, gt, _ = gf(inst)
                g = V3.ev_collab_k(inst, gr, gt, 1, **kw)
                row = _row(beta, n, seed)
                row.update({
                    "model": "V3",
                    "truck_only_makespan": round(v1["makespan"], 1),
                    "truck_only_tw_viol": v1["tw_viol"],
                    "greedy_makespan": _num(g["makespan"]),
                    "greedy_offloaded": g["offloaded"],
                    "greedy_tw_viol": g["tw_viol"],
                    "greedy_energy_inf": g["energy_inf"],
                    "greedy_payload_inf": g["payload_inf"],
                })
                for K in K_DRONES:
                    ev = (lambda K, kw: (lambda i, r, t:
                          V3.ev_lns_k(i, r, t, K, **kw)))(K, kw)
                    t0 = time.perf_counter()
                    lr, lt, _, _ = L.lns(inst, n, seed=seed, eval_fn=ev,
                                         greedy_fn=gf)
                    rt = time.perf_counter() - t0
                    l = V3.ev_collab_k(inst, lr, lt, K, **kw)
                    p = f"K{K}"
                    row[f"{p}_makespan"] = _num(l["makespan"])
                    row[f"{p}_offloaded"] = l["offloaded"]
                    row[f"{p}_tw_viol"] = l["tw_viol"]
                    row[f"{p}_energy_inf"] = l["energy_inf"]
                    row[f"{p}_payload_inf"] = l["payload_inf"]
                    row[f"{p}_recharges"] = l["recharges"]
                    row[f"{p}_runtime_s"] = round(rt, 2)
                rows.append(row)
    return rows


def w8_rows():
    """W8: K parallel serial drones on the FSTSP evaluator."""
    rows = []
    for beta in BETAS:
        kw = kw_of(beta)
        for n in SIZES:
            for s in range(N_SEEDS):
                seed = SEED_BASE + s
                inst = w6.make_instance(n, seed=seed)
                route0 = [0] + w6.nn_order(inst,
                                           list(inst["customers"].keys())) + [0]
                mk_truck = f7.fstsp_makespan(inst, route0, [], **kw)
                row = _row(beta, n, seed)
                row.update({"model": "W8", "truck_only_makespan":
                            round(mk_truck, 1)})
                for K in K_DRONES:
                    ev = (lambda K, kw: (lambda i, r, t:
                          f7.fstsp_makespan_multi(i, r, t, K, **kw)))(K, kw)
                    gf = (lambda K, kw: (lambda inst:
                          M.greedy_multi(inst, K, **kw)))(K, kw)
                    t0 = time.perf_counter()
                    gr, gt, goff = gf(inst)
                    mk_g = ev(inst, gr, gt)
                    _r, lt, mk_l, _ = L.lns(inst, n, seed=seed, eval_fn=ev,
                                            greedy_fn=gf)
                    rt = time.perf_counter() - t0
                    p = f"K{K}"
                    row[f"{p}_greedy_makespan"] = _num(mk_g)
                    row[f"{p}_greedy_offloaded"] = len(goff)
                    row[f"{p}_makespan"] = _num(mk_l)
                    row[f"{p}_offloaded"] = len(lt)
                    row[f"{p}_runtime_s"] = round(rt, 2)
                    if K == 1:
                        # the single-drone column, named as in the V3 table
                        row["greedy_makespan"] = _num(mk_g)
                        row["greedy_offloaded"] = len(goff)
                rows.append(row)
    return rows


def summarise(rows):
    out = []
    for model in ("V3", "W8"):
        for beta in BETAS:
            for n in SIZES:
                sub = [r for r in rows
                       if r["model"] == model and r["beta"] == beta
                       and r["size"] == n]
                if not sub:
                    continue
                srow = {"model": model, "beta": beta, "size": n,
                        "n_instances": len(sub),
                        "truck_only_makespan": round(_mean(
                            [r["truck_only_makespan"] for r in sub]), 1)}
                for c in CONFIGS:
                    cells = [r[f"{c}_makespan"] for r in sub]
                    finite = [float(x) for x in cells if x != ""]
                    srow[f"{c}_makespan"] = (round(_mean(finite), 1)
                                             if finite else "")
                    srow[f"{c}_feas_rate"] = round(
                        _mean([1.0 if x != "" else 0.0 for x in cells]), 2)
                    srow[f"{c}_imp_vs_truck_pct"] = round(_mean(
                        [(r["truck_only_makespan"] - float(r[f'{c}_makespan']))
                         / r["truck_only_makespan"] * 100
                         for r in sub if r[f"{c}_makespan"] != ""]), 1)
                    srow[f"{c}_offloaded"] = round(_mean(
                        [r[f"{c}_offloaded"] for r in sub]), 1)
                out.append(srow)
    return out


def control_lines(summary):
    """BETA = 0 must reproduce the committed range-only runs."""
    out = ["", "=" * 78,
           "CONTROL: BETA = 0.00 against the committed range-only runs",
           "=" * 78]
    checks = [("V3", os.path.join(HERE, "src", "results",
                                  "v3_ev_collab_summary.csv"),
               {"K1": "V3l_K1_makespan", "K2": "V3l_K2_makespan",
                "K3": "V3l_K3_makespan", "greedy": "V3g_makespan"}),
              ("W8", os.path.join(HERE, "src", "results",
                                  "week08_multidrone_summary.csv"),
               {"K1": "K1_lns_mk", "K2": "K2_lns_mk", "K3": "K3_lns_mk",
                "greedy": "K1_greedy_mk"})]
    for model, path, cols in checks:
        if not os.path.exists(path):
            out.append(f"  {model}: {os.path.basename(path)} not found, "
                       "control skipped")
            continue
        with open(path, encoding="utf-8") as fh:
            ref = {int(r["size"]): r for r in csv.DictReader(fh)}
        cells = []
        for c in CONFIGS:
            diffs = []
            for srow in summary:
                if srow["model"] != model or srow["beta"] != 0.0:
                    continue
                n = srow["size"]
                if n not in ref or srow[f"{c}_makespan"] == "":
                    continue
                diffs.append(abs(float(srow[f"{c}_makespan"])
                                 - float(ref[n][cols[c]])))
            cells.append(f"{c} max|diff|={max(diffs):.3f}" if diffs
                         else f"{c} n/a")
        out.append(f"  {model}: " + "  ".join(cells))
    return out


def main():
    res = os.path.join(HERE, "src", "results")
    os.makedirs(res, exist_ok=True)
    out_raw = os.path.join(res, "drone_energy_mainline_raw.csv")
    out_summary = os.path.join(res, "drone_energy_mainline_summary.csv")
    out_txt = os.path.join(res, "drone_energy_mainline_log.txt")

    rows = []
    Lg = []
    Lg.append("=" * 78)
    Lg.append("Drone energy and payload on the main line (V3 and W8)")
    Lg.append("=" * 78)
    Lg.append("models: V3 = EV + charging + time windows (K=1/2/3); "
              "W8 = FSTSP K parallel serial drones")
    Lg.append(f"BETA = {BETAS}   ALPHA={DE.ALPHA}  E_D={E_D}  P_MAX={P_MAX}"
              f"   (BETA=0 with E_D=R_D={w6.R_D} is the range-only control)")
    Lg.append(f"sizes={SIZES}  seeds={N_SEEDS} (base {SEED_BASE})  "
              f"drones K={K_DRONES}")
    Lg.extend(SI.env_lines())
    Lg.append("")
    t_all = time.perf_counter()

    Lg.append("--- V3: electric truck + charging + time windows ---")
    t0 = time.perf_counter()
    rows.extend(v3_rows())
    Lg.append(f"  V3 done in {time.perf_counter() - t0:.1f}s")
    Lg.append("--- W8: K parallel serial drones on the FSTSP evaluator ---")
    t0 = time.perf_counter()
    rows.extend(w8_rows())
    Lg.append(f"  W8 done in {time.perf_counter() - t0:.1f}s")

    summary = summarise(rows)

    for model, title in (("V3", "V3 -- electric truck + drone + charging + TW"),
                         ("W8", "W8 -- K parallel serial drones (FSTSP)")):
        Lg.append("")
        Lg.append("=" * 78)
        Lg.append(title)
        Lg.append("=" * 78)
        Lg.append("  BETA  N   truck |    greedy        K1            K2"
                  "            K3")
        for srow in summary:
            if srow["model"] != model:
                continue
            cells = []
            for c in CONFIGS:
                mk = srow[f"{c}_makespan"]
                rate = srow[f"{c}_feas_rate"]
                txt = (f"{mk:8.1f}" if mk != "" else "     n/a")
                if rate < 1.0:
                    txt += f"({rate:.2f})"
                cells.append(txt + f" {srow[f'{c}_imp_vs_truck_pct']:5.1f}%")
            Lg.append(f"  {srow['beta']:5.2f} {srow['size']:2d} "
                      f"{srow['truck_only_makespan']:7.1f} | " +
                      " ".join(cells))

    # headline: the effect of switching the payload/energy gates on
    Lg.append("")
    Lg.append("=" * 78)
    Lg.append("EFFECT OF THE ENERGY/PAYLOAD GATES (mean over sizes)")
    Lg.append("=" * 78)
    Lg.append("  model | config | BETA=0.00 makespan | BETA=0.02 makespan | "
              "delta | feasible at 0.02")
    for model in ("V3", "W8"):
        for c in CONFIGS:
            b0 = [s for s in summary
                  if s["model"] == model and s["beta"] == 0.0
                  and s[f"{c}_makespan"] != ""]
            b2 = [s for s in summary
                  if s["model"] == model and s["beta"] == 0.02
                  and s[f"{c}_makespan"] != ""]
            m0 = _mean([s[f"{c}_makespan"] for s in b0])
            m2 = _mean([s[f"{c}_makespan"] for s in b2])
            rate = _mean([s[f"{c}_feas_rate"] for s in summary
                          if s["model"] == model and s["beta"] == 0.02])
            delta = (f"{(m2 - m0) / m0 * 100:+6.1f}%" if b0 and b2 else "  n/a")
            Lg.append(f"  {model:5s} | {c:6s} | {m0:19.1f} | {m2:19.1f} | "
                      f"{delta} | {rate:.2f}")
    Lg.append("")
    Lg.append("  infeasible plans under BETA = 0.02 (instances with makespan "
              "inf):")
    for model in ("V3", "W8"):
        sub = [r for r in rows if r["model"] == model and r["beta"] == 0.02]
        counts = [f"{c} {sum(1 for r in sub if r[f'{c}_makespan'] == '')}"
                  f"/{len(sub)}" for c in CONFIGS]
        extra = ""
        if model == "V3":
            extra = ("   (K1 payload-cap violations: "
                     f"{sum(1 for r in sub if r['K1_payload_inf'])})")
        Lg.append(f"    {model}: " + "  ".join(counts) + extra)
    Lg.append("")
    Lg.extend(control_lines(summary))
    Lg.append("")
    Lg.append(f"total wall-clock: {time.perf_counter() - t_all:.1f}s")
    Lg.append(f"[raw -> {out_raw}]")
    Lg.append(f"[summary -> {out_summary}]")
    Lg.append(f"[log -> {out_txt}]")

    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(out_raw, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(out_summary, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    text = "\n".join(Lg)
    with open(out_txt, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
