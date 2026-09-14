"""
ALNS for the physical FSTSP model (the model the exact study uses).

Why this module exists
----------------------
`week08_lns` runs a destroy-and-repair LNS whose destroy size is capped at
`min(8, n // 4)` -- that is 2 customers at n=10 -- and whose repair is a single
greedy rule. The CP-SAT comparison in `week08_exact_gap` then showed that from
n=10 on the exact model's own feasible plan is 8.8-17.5% *better* than what that
LNS finds. So there is room on the search side, which is what this module
attacks:

  * larger destroys (up to ~35% of the customers, not 2-4);
  * five destroy operators: random, worst, related (Shaw), route segment, whole
    sorties;
  * a regret-2 repair next to the plain greedy one;
  * **adaptive** operator weights (the A in ALNS): every segment of iterations
    the operators are re-weighted by the scores they earned, so the search shifts
    towards whatever is working on this instance.

Objective and feasibility are exactly those of the exact study: every candidate
is evaluated with `cpsat_fstsp.fstsp_makespan_clean` (one serial drone, launch
before recovery, range, truck waits), so the comparison against the CP-SAT primal
solution is like for like.

Determinism: one RNG seeded from the instance seed and a fixed iteration budget,
so a re-run reproduces the same numbers.

Run:
  python src/experiments/alns_fstsp.py
"""

import os
import sys
import math
import random
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6
import week08_lns as L
import cpsat_fstsp as X
import sysinfo as SI

EVAL = X.fstsp_makespan_clean
INF = float("inf")
dist = w6.dist
R_D = w6.R_D

# --- ALNS parameters -------------------------------------------------------
Q_FRAC = 0.35            # destroy size = max(2, round(Q_FRAC * n))
ITERS_PER_N = 100        # iteration budget = ITERS_PER_N * n
SEGMENT = 120            # iterations between operator-weight updates
RHO = 0.30               # weight smoothing factor
SIGMA_BEST = 12.0        # score for a new global best
SIGMA_IMPROVE = 6.0      # score for improving the current solution
SIGMA_ACCEPT = 2.0       # score for an accepted worse solution
T0_FRAC = 0.06           # initial SA temperature = 6% of the current makespan
T_END_FRAC = 0.002       # final temperature as a fraction of the initial one
MAX_CUST = 2
DESTROY_OPS = ("random", "worst", "related", "segment", "sortie")
REPAIR_OPS = ("greedy", "regret2")


# ---------------------------------------------------------------------------
# state helpers
# ---------------------------------------------------------------------------
def all_customers(inst):
    return list(inst["customers"].keys())


def mk_of(inst, route, trips, rd=R_D):
    return EVAL(inst, route, trips, rd)


def _pending_after(inst, route, trips, chosen, rd=R_D):
    """Remove `chosen` from the plan; returns (route, trips, removed_set)."""
    return L.destroy(inst, route, trips, chosen)


# ---------------------------------------------------------------------------
# destroy operators
# ---------------------------------------------------------------------------
def d_random(inst, route, trips, q, rng, rd=R_D):
    custs = all_customers(inst)
    chosen = rng.sample(custs, min(q, len(custs)))
    return _pending_after(inst, route, trips, chosen, rd)


def d_worst(inst, route, trips, q, rng, rd=R_D):
    """Remove the customers whose removal lowers the makespan most."""
    base = mk_of(inst, route, trips, rd)
    gains = []
    for c in all_customers(inst):
        r2, t2, _ = _pending_after(inst, route, trips, [c], rd)
        m = mk_of(inst, r2, t2, rd)
        gains.append((base - m, rng.random(), c))
    gains.sort(reverse=True)
    chosen = [c for _g, _t, c in gains[:q]]
    return _pending_after(inst, route, trips, chosen, rd)


def d_related(inst, route, trips, q, rng, rd=R_D):
    """Shaw/related removal: grow a set seeded by one customer, always adding the
    customer closest to the set already chosen."""
    custs = all_customers(inst)
    if not custs:
        return route[:], list(trips), set()
    chosen = [rng.choice(custs)]
    while len(chosen) < min(q, len(custs)):
        best_c, best_d = None, INF
        for c in custs:
            if c in chosen:
                continue
            dmin = min(dist(inst, c, x) for x in chosen)
            if dmin < best_d - 1e-9:
                best_c, best_d = c, dmin
        if best_c is None:
            break
        chosen.append(best_c)
    return _pending_after(inst, route, trips, chosen, rd)


def d_segment(inst, route, trips, q, rng, rd=R_D):
    """Remove a contiguous slice of the truck route."""
    truck = [c for c in route if c != 0]
    if not truck:
        return d_related(inst, route, trips, q, rng, rd)
    span = min(q, len(truck))
    start = rng.randrange(0, len(truck) - span + 1)
    return _pending_after(inst, route, trips, truck[start:start + span], rd)


def d_sortie(inst, route, trips, q, rng, rd=R_D):
    """Remove whole drone sorties until at least q customers are gone."""
    if not trips:
        return d_segment(inst, route, trips, q, rng, rd)
    order = list(range(len(trips)))
    rng.shuffle(order)
    chosen = []
    for idx in order:
        _ln, custs, _rn = trips[idx]
        chosen.extend(custs)
        if len(chosen) >= q:
            break
    return _pending_after(inst, route, trips, chosen, rd)


DESTROY = {"random": d_random, "worst": d_worst, "related": d_related,
           "segment": d_segment, "sortie": d_sortie}


# ---------------------------------------------------------------------------
# repair operators
# ---------------------------------------------------------------------------
def _best_insertion(inst, route, trips, c, pool, rd=R_D, max_cust=MAX_CUST):
    """The three candidate ways to (re)insert c, each already evaluated.

    Returns a list of (makespan, kind, payload) with one entry per kind:
    'truck' (position), 'drone' (single-customer sortie) and 'pair' (two
    customers in one sortie). Truck insertion is always available, so the list
    is never empty.
    """
    out = []
    # truck
    best = (INF, "truck", None)
    for p in range(1, len(route)):
        cand = route[:p] + [c] + route[p:]
        m = mk_of(inst, cand, trips, rd)
        if m < best[0] - 1e-9:
            best = (m, "truck", (p,))
    out.append(best)
    # drone sortie launched/recovered at nearby truck nodes
    near = L._near_positions(inst, route, c)
    best_d = (INF, "drone", None)
    best_p = (INF, "pair", None)
    for ai in range(len(near)):
        i = near[ai]
        a = route[i]
        for bj in range(ai + 1, len(near)):
            j = near[bj]
            b = route[j]
            if dist(inst, a, c) + dist(inst, c, b) <= rd + 1e-9:
                m = mk_of(inst, route, trips + [(a, (c,), b)], rd)
                if m < best_d[0] - 1e-9:
                    best_d = (m, "drone", (a, (c,), b))
            if max_cust >= 2:
                for c2 in pool:
                    if c2 == c:
                        continue
                    for order in ((c, c2), (c2, c)):
                        dd = (dist(inst, a, order[0]) + dist(inst, order[0], order[1])
                              + dist(inst, order[1], b))
                        if dd > rd + 1e-9:
                            continue
                        m = mk_of(inst, route, trips + [(a, order, b)], rd)
                        if m < best_p[0] - 1e-9:
                            best_p = (m, "pair", (a, order, b))
    if best_d[2] is not None:
        out.append(best_d)
    if best_p[2] is not None:
        out.append(best_p)
    return out


def _apply(route, trips, kind, payload, c):
    if kind == "truck":
        p = payload[0]
        return route[:p] + [c] + route[p:], list(trips)
    a, custs, b = payload
    return route[:], list(trips) + [(a, custs, b)]


def r_greedy(inst, route, trips, pending, rng, rd=R_D, max_cust=MAX_CUST):
    pending = list(pending)
    while pending:
        c = pending.pop(0)
        options = _best_insertion(inst, route, trips, c, pending, rd, max_cust)
        m, kind, payload = min(options, key=lambda o: o[0])
        route, trips = _apply(route, trips, kind, payload, c)
        if kind == "pair":
            for x in payload[1]:
                if x in pending:
                    pending.remove(x)
    return route, trips


def r_regret2(inst, route, trips, pending, rng, rd=R_D, max_cust=MAX_CUST):
    """Insert the customer with the largest regret (second best option minus
    best option) first."""
    pending = list(pending)
    while pending:
        best_choice = None
        for c in pending:
            pool = [x for x in pending if x != c]
            options = sorted(_best_insertion(inst, route, trips, c, pool, rd,
                                             max_cust), key=lambda o: o[0])
            regret = (options[1][0] - options[0][0]) if len(options) > 1 else 0.0
            if best_choice is None or regret > best_choice[0] + 1e-9:
                best_choice = (regret, c, options[0])
        _reg, c, (m, kind, payload) = best_choice
        route, trips = _apply(route, trips, kind, payload, c)
        pending.remove(c)
        if kind == "pair":
            for x in payload[1]:
                if x in pending:
                    pending.remove(x)
    return route, trips


REPAIR = {"greedy": r_greedy, "regret2": r_regret2}


# ---------------------------------------------------------------------------
# the ALNS itself
# ---------------------------------------------------------------------------
def alns(inst, seed=0, rd=R_D, iters=None, max_cust=MAX_CUST,
         start=None, eval_fn=None, adaptive=True):
    """Adaptive large neighbourhood search on the physical FSTSP model.

    start    : optional (route, trips) to start from; default the clean greedy
    iters    : iteration budget; default ITERS_PER_N * n
    adaptive : when False the operator weights stay uniform, which is the
               ablation that isolates the "A" in ALNS
    Returns (route, trips, best_makespan, iters, history) where history is the
    list of per-segment best makespans (for diagnostics).
    """
    n = inst["n"]
    eval_fn = eval_fn or EVAL
    if start is None:
        start = X.clean_greedy(inst, max_cust=max_cust)[:2]
    route, trips = start[0][:], list(start[1])
    cur = eval_fn(inst, route, trips, rd)
    best_route, best_trips, best = route[:], list(trips), cur

    rng = random.Random(seed)
    if iters is None:
        iters = ITERS_PER_N * n
    q_max = max(2, int(round(Q_FRAC * n)))
    q_min = 2
    T = T0_FRAC * max(cur, 1.0)
    cool = (T_END_FRAC) ** (1.0 / max(1, iters))

    w_d = {op: 1.0 for op in DESTROY_OPS}
    w_r = {op: 1.0 for op in REPAIR_OPS}
    score_d = {op: 0.0 for op in DESTROY_OPS}
    score_r = {op: 0.0 for op in REPAIR_OPS}
    uses_d = {op: 0 for op in DESTROY_OPS}
    uses_r = {op: 0 for op in REPAIR_OPS}

    def roulette(weights):
        total = sum(weights.values())
        pick = rng.random() * total
        acc = 0.0
        for k, w in weights.items():
            acc += w
            if pick <= acc:
                return k
        return next(iter(weights))

    history = []
    for it in range(iters):
        dop = roulette(w_d)
        rop = roulette(w_r)
        q = rng.randint(q_min, min(q_max, len(all_customers(inst))))
        r2, t2, removed = DESTROY[dop](inst, route, trips, q, rng, rd)
        if not removed:
            continue
        pending = list(removed)
        rng.shuffle(pending)
        r2, t2 = REPAIR[rop](inst, r2, t2, pending, rng, rd, max_cust)
        m2 = eval_fn(inst, r2, t2, rd)
        if m2 == INF:
            T *= cool
            continue

        score = 0.0
        if m2 < best - 1e-9:
            route, trips, cur = r2, t2, m2
            best_route, best_trips, best = r2[:], list(t2), m2
            score = SIGMA_BEST
        elif m2 < cur - 1e-9:
            route, trips, cur = r2, t2, m2
            score = SIGMA_IMPROVE
        elif rng.random() < math.exp(-(m2 - cur) / max(T, 1e-9)):
            route, trips, cur = r2, t2, m2
            score = SIGMA_ACCEPT
        score_d[dop] += score
        score_r[rop] += score
        uses_d[dop] += 1
        uses_r[rop] += 1

        if adaptive and (it + 1) % SEGMENT == 0:
            for op in DESTROY_OPS:
                if uses_d[op]:
                    w_d[op] = ((1 - RHO) * w_d[op]
                               + RHO * score_d[op] / uses_d[op])
            for op in REPAIR_OPS:
                if uses_r[op]:
                    w_r[op] = ((1 - RHO) * w_r[op]
                               + RHO * score_r[op] / uses_r[op])
            score_d = {op: 0.0 for op in DESTROY_OPS}
            score_r = {op: 0.0 for op in REPAIR_OPS}
            uses_d = {op: 0 for op in DESTROY_OPS}
            uses_r = {op: 0 for op in REPAIR_OPS}
            history.append(round(best, 2))
        T *= cool
    return best_route, best_trips, best, iters, history


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
SIZES = [8, 10, 12, 14, 16]
N_SEEDS = 5
SEED_BASE = 20260720


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def _cp_sat_primal(path):
    """Best feasible plan CP-SAT found, per (size, seed), if the exact study has
    been run (its raw CSV is git-ignored, so this is optional)."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("opt"):
                out[(int(r["size"]), int(r["seed"]))] = float(r["opt"])
    return out


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    os.makedirs(res, exist_ok=True)
    out_raw = os.path.join(res, "week08_alns_raw.csv")
    out_sum = os.path.join(res, "week08_alns_summary.csv")
    out_txt = os.path.join(res, "week08_alns_log.txt")
    primal = _cp_sat_primal(os.path.join(res, "week08_exact_gap_raw.csv"))

    rows = []
    Lg = ["=" * 78,
          "ALNS on the physical FSTSP model (vs the existing LNS and CP-SAT)",
          "=" * 78,
          f"sizes={SIZES} seeds={N_SEEDS} base {SEED_BASE} max_cust={MAX_CUST}",
          f"destroy operators={DESTROY_OPS}",
          f"repair operators={REPAIR_OPS}",
          f"destroy size = max(2, {Q_FRAC} * n); iterations = {ITERS_PER_N} * n",
          "adaptive run vs fixed-weight run (same budget, same seed): the "
          "ablation for the operator weights",
          f"adaptive weights: segment={SEGMENT}, rho={RHO}, "
          f"scores={SIGMA_BEST}/{SIGMA_IMPROVE}/{SIGMA_ACCEPT}"]
    Lg.extend(SI.env_lines())
    Lg.append("")
    for n in SIZES:
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)
            t0 = time.perf_counter()
            gr, gt, _ = X.clean_greedy(inst, max_cust=MAX_CUST)
            mk_greedy = EVAL(inst, gr, gt)
            lr, lt, _, _ = L.lns(inst, n, seed=seed, max_cust=MAX_CUST,
                                 eval_fn=EVAL,
                                 greedy_fn=lambda i: X.clean_greedy(
                                     i, max_cust=MAX_CUST))
            mk_lns = EVAL(inst, lr, lt)
            ar, at, mk_alns, iters, hist = alns(inst, seed=seed,
                                                start=(lr, lt),
                                                adaptive=True)
            mk_alns = EVAL(inst, ar, at)
            fr, ft, mk_fixed, _it2, _h2 = alns(inst, seed=seed,
                                               start=(lr, lt),
                                               adaptive=False)
            mk_fixed = EVAL(inst, fr, ft)
            rt = time.perf_counter() - t0
            cp = primal.get((n, seed))
            row = {
                "size": n, "seed": seed,
                "greedy_mk": round(mk_greedy, 2),
                "lns_mk": round(mk_lns, 2),
                "alns_mk": round(mk_alns, 2),
                "alns_fixed_mk": round(mk_fixed, 2),
                "alns_iters": iters,
                "alns_imp_vs_lns_pct": round((mk_lns - mk_alns) / mk_lns * 100, 2),
                "alns_imp_vs_greedy_pct": round(
                    (mk_greedy - mk_alns) / mk_greedy * 100, 2),
                "adaptive_vs_fixed_pct": round(
                    (mk_fixed - mk_alns) / mk_fixed * 100, 2),
                "cp_sat_primal": (round(cp, 2) if cp else ""),
                "alns_gap_vs_cp_pct": (
                    round((mk_alns - cp) / cp * 100, 2) if cp else ""),
                "runtime_s": round(rt, 2),
            }
            rows.append(row)
            print(f"n={n} seed={seed}: greedy {row['greedy_mk']:.1f} | "
                  f"LNS {row['lns_mk']:.1f} | ALNS {row['alns_mk']:.1f} "
                  f"({row['alns_imp_vs_lns_pct']:+.2f}%)"
                  + (f" | CP-SAT {row['cp_sat_primal']:.1f} "
                     f"(gap {row['alns_gap_vs_cp_pct']:+.1f}%)"
                     if cp else "")
                  + f" | {rt:.1f}s", flush=True)

    summary = []
    for n in SIZES:
        sub = [r for r in rows if r["size"] == n]
        with_cp = [r for r in sub if r["alns_gap_vs_cp_pct"] != ""]
        summary.append({
            "size": n, "n_instances": len(sub),
            "greedy_mk": round(_mean([r["greedy_mk"] for r in sub]), 2),
            "lns_mk": round(_mean([r["lns_mk"] for r in sub]), 2),
            "alns_mk": round(_mean([r["alns_mk"] for r in sub]), 2),
            "alns_fixed_mk": round(_mean([r["alns_fixed_mk"] for r in sub]), 2),
            "adaptive_vs_fixed_mean_pct": round(
                _mean([r["adaptive_vs_fixed_pct"] for r in sub]), 2),
            "alns_imp_vs_lns_mean_pct": round(
                _mean([r["alns_imp_vs_lns_pct"] for r in sub]), 2),
            "alns_imp_vs_lns_min_pct": round(
                min(r["alns_imp_vs_lns_pct"] for r in sub), 2),
            "alns_imp_vs_lns_max_pct": round(
                max(r["alns_imp_vs_lns_pct"] for r in sub), 2),
            "alns_imp_vs_greedy_mean_pct": round(
                _mean([r["alns_imp_vs_greedy_pct"] for r in sub]), 2),
            "cp_sat_primal_mk": (round(_mean(
                [r["cp_sat_primal"] for r in with_cp]), 2) if with_cp else ""),
            "alns_gap_vs_cp_mean_pct": (round(_mean(
                [r["alns_gap_vs_cp_pct"] for r in with_cp]), 2)
                if with_cp else ""),
            "runtime_s": round(_mean([r["runtime_s"] for r in sub]), 2),
        })
    Lg.append("")
    for srow in summary:
        Lg.append(f"  N={srow['size']:2d}: greedy {srow['greedy_mk']:7.1f} | "
                  f"LNS {srow['lns_mk']:7.1f} | ALNS {srow['alns_mk']:7.1f} "
                  f"({srow['alns_imp_vs_lns_mean_pct']:+.2f}% vs LNS, "
                  f"{srow['alns_imp_vs_lns_min_pct']:+.2f}.."
                  f"{srow['alns_imp_vs_lns_max_pct']:+.2f}) | fixed-weight "
                  f"{srow['alns_fixed_mk']:7.1f} (adaptive "
                  f"{srow['adaptive_vs_fixed_mean_pct']:+.2f}%)"
                  + (f" | CP-SAT {srow['cp_sat_primal_mk']:7.1f} "
                     f"(gap {srow['alns_gap_vs_cp_mean_pct']:+.2f}%)"
                     if srow["cp_sat_primal_mk"] != "" else ""))

    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(out_raw, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(out_sum, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    text = "\n".join(Lg)
    with open(out_txt, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]\n[summary -> {out_sum}]\n[log -> {out_txt}]")


if __name__ == "__main__":
    main()
