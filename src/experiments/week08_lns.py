"""
Week 8 -- Large Neighborhood Search (LNS) improvement on the ground-air
collaborative heuristic.

Why this module exists
----------------------
My V2 heuristic (week07_improvement_ablation.my_v2_param) is a *constructive*
greedy: it starts from a nearest-neighbour truck route and repeatedly offloads
the best drone sortie it can find.  Once no single offload improves the
makespan it stops, so the result is a local optimum of that insertion order.
The scale study (week06_largeN) shows the collaborative gain collapses as N
grows, which is what one expects from a greedy with no improvement phase.

This module adds an improvement phase -- a destroy-and-repair LNS -- on top of
the same V2 solution and measures how much it helps on the same instances.

State
-----
  route        : [0, ...truck nodes..., 0]; customers served by the drone are
                 NOT in the route (the truck route is the drone-free backbone)
  drone_trips  : list of (launch_node, custs_tuple, recover_node)

Objective: FSTSP completion time, evaluated by the shared sequential evaluator
`week07_fstsp_repro.fstsp_makespan` (single serial drone, sync enforced) so the
comparison against the greedy V2 and the published baseline is apples-to-apples.

LNS
---
  destroy : remove q customers -- random / "worst" (largest removal saving) /
            a whole drone sortie.
  repair  : reinsert every removed customer, each time choosing the option that
            minimises the makespan:
              (a) insert into the truck route at its best position;
              (b) a single-customer drone sortie;
              (c) pair it with another removed customer in one sortie.
  accept  : simulated annealing (accept a worse solution with prob
            exp(-delta/T)); the best solution seen is kept.

Determinism: one RNG seeded from the instance seed, so a re-run reproduces the
same numbers (given the same iteration budget).

Run:
  python src/experiments/week08_lns.py
"""

import os
import sys
import time
import math
import csv
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab
import sysinfo as SI

V_T = w6.V_T
V_D = w6.V_D
SERVICE = w6.SERVICE
R_D = w6.R_D
dist = w6.dist
makespan = f7.fstsp_makespan

# per-size budget: iterations of destroy-repair, and max customers destroyed
ITERS = {8: 300, 12: 300, 16: 300, 20: 400, 30: 250, 50: 150}
NEAR_K = 10          # launch/recover candidates kept per customer (plus depot)
T0_RATIO = 0.05      # initial SA temperature = 5% of the current makespan
T_END_RATIO = 0.001  # final temperature fraction (cooling reach)


def all_customers(inst):
    return list(inst["customers"].keys())


def two_opt(inst, route, trips, max_passes=10, eval_fn=makespan):
    """Intra-route 2-opt on the truck backbone with the drone trips fixed.
    Accept a move only if the exact evaluator says the makespan improves."""
    route = route[:]
    base = eval_fn(inst, route, trips)
    moves = 0
    for _ in range(max_passes):
        improved = False
        seq = route[1:-1]
        m = len(seq)
        for a in range(m - 1):
            for b in range(a + 1, m):
                rev = seq[:a] + seq[a:b + 1][::-1] + seq[b + 1:]
                cand = [0] + rev + [0]
                nm = eval_fn(inst, cand, trips)
                if nm < base - 1e-9:
                    route, base, seq, improved = cand, nm, rev, True
                    moves += 1
        if not improved:
            break
    return route, trips, base, moves


def destroy(inst, route, trips, chosen):
    """Remove `chosen` customers from the solution.

    A drone customer is dropped from its sortie; a truck customer is dropped
    from the route, and any sortie that used it as launch/recover is dissolved
    (the customers of that sortie are re-queued for repair)."""
    route = route[:]
    trips = list(trips)
    removed = set(chosen)
    for c in chosen:
        # drone-served customer?
        hit = False
        for idx in range(len(trips)):
            ln, custs, rn = trips[idx]
            if c in custs:
                rest = tuple(x for x in custs if x != c)
                trips[idx] = (ln, rest, rn) if rest else None
                hit = True
                break
        trips = [t for t in trips if t is not None]
        if hit:
            continue
        # truck-served customer
        if c in route:
            route.remove(c)
        keep = []
        for ln, custs, rn in trips:
            if ln == c or rn == c:
                removed.update(custs)
            else:
                keep.append((ln, custs, rn))
        trips = keep
    return route, trips, removed


def _near_positions(inst, route, c, k=NEAR_K):
    """Route positions to consider as launch/recover for customer c: the k
    nearest nodes plus the two depot bookends, returned in route order."""
    idx = sorted(range(len(route)), key=lambda p: dist(inst, route[p], c))
    keep = set(idx[:k]) | {0, len(route) - 1}
    return sorted(keep)


def _best_reinsertion(inst, route, trips, c, pool, rd, max_cust,
                      eval_fn=makespan):
    """Return (makespan, kind, payload) for the cheapest way to (re)insert c.

    kind: 'truck' -> payload (pos,)
          'drone' -> payload (launch, (c,), recover)
          'pair'  -> payload (launch, (c, c2) or (c2, c), recover)
    The returned makespan is always finite (truck insertion is always open)."""
    best = (float("inf"), None, None)

    # (a) insert into the truck route at its best position
    for p in range(1, len(route)):
        cand = route[:p] + [c] + route[p:]
        m = eval_fn(inst, cand, trips)
        if m < best[0] - 1e-9:
            best = (m, "truck", (p,))

    # (b)/(c) drone sorties launched/recovered at nearby route nodes
    pos = _near_positions(inst, route, c)
    for ai in range(len(pos)):
        i = pos[ai]
        a = route[i]
        for bj in range(ai + 1, len(pos)):
            j = pos[bj]
            b = route[j]
            if dist(inst, a, c) + dist(inst, c, b) <= rd:
                m = eval_fn(inst, route, trips + [(a, (c,), b)])
                if m < best[0] - 1e-9:
                    best = (m, "drone", (a, (c,), b))
            if max_cust >= 2:
                for c2 in pool:
                    for order in ((c, c2), (c2, c)):
                        d = dist(inst, a, order[0]) + dist(inst, order[0], order[1]) \
                            + dist(inst, order[1], b)
                        if d > rd:
                            continue
                        m = eval_fn(inst, route, trips + [(a, order, b)])
                        if m < best[0] - 1e-9:
                            best = (m, "pair", (a, order, b))
    return best


def _choose_customers(inst, route, trips, rng, q):
    """Pick the customers to destroy: sometimes a whole sortie, sometimes the
    q customers with the largest truck-removal saving, otherwise random."""
    mode = rng.random()
    if mode < 0.30 and trips:
        _, cs, _ = rng.choice(trips)
        return list(cs)
    truck_custs = [x for x in route if x != 0]
    if mode < 0.55 and len(truck_custs) >= q:
        ranked = sorted(truck_custs,
                        key=lambda c: f7._remove_saving(inst, route, c),
                        reverse=True)
        return ranked[:q]
    allc = all_customers(inst)
    return rng.sample(allc, min(q, len(allc)))


def lns(inst, size, seed=0, rd=R_D, max_cust=2, iters=None, q_max=None,
        eval_fn=makespan, greedy_fn=None):
    """Destroy-and-repair LNS seeded from the greedy V2 solution.

    eval_fn  : evaluator (inst, route, trips) -> makespan; defaults to the
               single-drone FSTSP evaluator (multi-drone runs pass their own).
    greedy_fn: optional greedy constructor (inst) -> (route, trips, offloaded);
               defaults to the standard single-drone V2 greedy."""
    iters = iters if iters is not None else ITERS.get(size, 60)
    if q_max is None:
        q_max = max(2, min(8, size // 4))

    rng = random.Random(seed)
    if greedy_fn is None:
        route, trips, _ = ab.my_v2_param(inst, max_cust=max_cust,
                                         multi_takeoff=True, drone_range=rd)
    else:
        route, trips, _ = greedy_fn(inst)
    cur = eval_fn(inst, route, trips)
    best_route, best_trips, best_mk = route[:], list(trips), cur

    if cur <= 0 or cur == float("inf"):
        return best_route, best_trips, best_mk, iters

    alpha = (T_END_RATIO) ** (1.0 / max(1, iters))
    T = T0_RATIO * cur
    customers = all_customers(inst)

    for _ in range(iters):
        q = rng.randint(1, min(q_max, len(customers)))
        chosen = _choose_customers(inst, route, trips, rng, q)
        r2, t2, removed = destroy(inst, route, trips, chosen)

        pending = list(removed)
        rng.shuffle(pending)
        feasible = True
        while pending:
            c = pending.pop(0)
            mk_new, kind, data = _best_reinsertion(
                inst, r2, t2, c, pending, rd, max_cust, eval_fn)
            if kind is None:
                feasible = False
                break
            if kind == "truck":
                p = data[0]
                r2 = r2[:p] + [c] + r2[p:]
            else:
                a, custs, b = data
                t2 = t2 + [(a, custs, b)]
                for x in custs:
                    if x in pending:
                        pending.remove(x)
            pending = [x for x in pending if x != c]
        if not feasible:
            T *= alpha
            continue

        new_mk = eval_fn(inst, r2, t2)
        delta = new_mk - cur
        if delta < -1e-9 or rng.random() < math.exp(-delta / max(T, 1e-9)):
            route, trips, cur = r2, t2, new_mk
            if new_mk < best_mk - 1e-9:
                best_route, best_trips, best_mk = r2[:], list(t2), new_mk
        T *= alpha

    return best_route, best_trips, best_mk, iters


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week08_lns_raw.csv")
    out_summary = os.path.join(res_dir, "week08_lns_summary.csv")
    out_txt = os.path.join(res_dir, "week08_lns_log.txt")

    N_SEEDS = 10
    SIZES = [8, 12, 16, 20, 30, 50]
    SEED_BASE = 20260720

    L = []
    L.append("=" * 78)
    L.append("WEEK 8 -- LNS improvement on the ground-air collaborative heuristic")
    L.append("=" * 78)
    L.append(f"seeds={N_SEEDS} (base {SEED_BASE}..{SEED_BASE + N_SEEDS - 1})  "
             f"sizes={SIZES}")
    L.append(f"truck_speed={V_T}  drone_speed={V_D}  drone_range={R_D}  "
             f"service={SERVICE}")
    L.append("shared evaluator: FSTSP completion time, ONE serial drone, "
             "sync enforced")
    L.append("methods: truck-only | V2 greedy | V2 greedy + 2-opt | V2 greedy + LNS")
    L.append(f"iterations per size (destroy-repair): {ITERS}")
    L.extend(SI.env_lines())
    L.append("")

    raw_rows = []
    acc = {n: {} for n in SIZES}
    for n in SIZES:
        acc[n] = {k: [] for k in ["truck", "greedy", "opt2", "lns"]}
        acc[n]["iters"] = ITERS.get(n)
        acc[n]["rt"] = []

    for n in SIZES:
        L.append(f"=== size N={n} ===")
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)

            truck_route = [0] + w6.nn_order(inst, all_customers(inst)) + [0]
            mk_truck = makespan(inst, truck_route, [])

            t0 = time.perf_counter()
            g_route, g_trips, g_off = ab.my_v2_param(
                inst, max_cust=2, multi_takeoff=True)
            mk_greedy = makespan(inst, g_route, g_trips)

            o_route, o_trips, mk_opt2, o_moves = two_opt(inst, g_route, g_trips)

            l_route, l_trips, mk_lns, iters = lns(inst, n, seed=seed)
            rt = time.perf_counter() - t0

            row = {
                "size": n, "seed": seed,
                "truck_only_mk": round(mk_truck, 1),
                "greedy_mk": round(mk_greedy, 1),
                "greedy_off": len(g_off),
                "opt2_mk": round(mk_opt2, 1),
                "opt2_moves": o_moves,
                "lns_mk": round(mk_lns, 1),
                "lns_off": len(l_trips),
                "lns_iters": iters,
                "runtime_s": round(rt, 2),
            }
            row["imp_greedy_vs_truck_pct"] = round(
                (mk_truck - mk_greedy) / mk_truck * 100, 1)
            row["imp_lns_vs_truck_pct"] = round(
                (mk_truck - mk_lns) / mk_truck * 100, 1)
            row["imp_lns_vs_greedy_pct"] = round(
                (mk_greedy - mk_lns) / mk_greedy * 100, 2)
            raw_rows.append(row)

            acc[n]["truck"].append(mk_truck)
            acc[n]["greedy"].append(mk_greedy)
            acc[n]["opt2"].append(mk_opt2)
            acc[n]["lns"].append(mk_lns)
            acc[n]["rt"].append(rt)

            L.append(
                f"  seed {seed}: truck={mk_truck:7.1f} "
                f"greedy={mk_greedy:7.1f} opt2={mk_opt2:7.1f} "
                f"LNS={mk_lns:7.1f}  LNS-greedy={row['imp_lns_vs_greedy_pct']:5.2f}%  "
                f"off={row['lns_off']}/{n}  {rt:.2f}s")
        L.append("")

    # ---- aggregate ----
    L.append("=" * 78)
    L.append("AGGREGATE (mean over seeds per size)")
    L.append("=" * 78)
    summary_rows = []
    for n in SIZES:
        t = acc[n]["truck"]
        g = acc[n]["greedy"]
        o = acc[n]["opt2"]
        l = acc[n]["lns"]
        srow = {
            "size": n,
            "n_instances": N_SEEDS,
            "iters": acc[n]["iters"],
            "truck_only_mk": round(_mean(t), 1),
            "greedy_mk": round(_mean(g), 1),
            "opt2_mk": round(_mean(o), 1),
            "lns_mk": round(_mean(l), 1),
            "greedy_imp_vs_truck_pct": round(
                _mean([(a - b) / a * 100 for a, b in zip(t, g)]), 1),
            "lns_imp_vs_truck_pct": round(
                _mean([(a - b) / a * 100 for a, b in zip(t, l)]), 1),
            "lns_imp_vs_greedy_pct": round(
                _mean([(a - b) / a * 100 for a, b in zip(g, l)]), 2),
            "opt2_imp_vs_greedy_pct": round(
                _mean([(a - b) / a * 100 for a, b in zip(g, o)]), 2),
            "lns_runtime_mean_s": round(_mean(acc[n]["rt"]), 2),
        }
        summary_rows.append(srow)
        L.append(
            f"  N={n:2d}: truck={srow['truck_only_mk']:7.1f}  "
            f"greedy={srow['greedy_mk']:7.1f} ({srow['greedy_imp_vs_truck_pct']:5.1f}%)  "
            f"opt2={srow['opt2_mk']:7.1f}  "
            f"LNS={srow['lns_mk']:7.1f} ({srow['lns_imp_vs_truck_pct']:5.1f}%)  "
            f"LNS-greedy={srow['lns_imp_vs_greedy_pct']:5.2f}%  "
            f"{srow['lns_runtime_mean_s']:.1f}s/it")
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
