"""Validation of the CP-SAT exact FSTSP model.

Two independent checks:

  * with the drone range set to zero the model must reduce to a plain truck TSP,
    so its optimum must equal a Held-Karp TSP optimum (routing + timing);
  * on a tiny instance (n=5) the CP-SAT optimum must equal an exhaustive
    enumeration of the whole physical solution space (truck route + serial
    sorties), which validates the drone timing and the single-drone constraint.
"""

import math
from itertools import permutations

import pytest

import week06_ground_air_evrp_tw as w6
import cpsat_fstsp as X

INF = float("inf")


def held_karp(inst, nodes):
    pts = [0] + list(nodes)
    m = len(pts)
    d = [[w6.dist(inst, a, b) / w6.V_T for b in pts] for a in pts]
    dp = [[INF] * m for _ in range(1 << m)]
    dp[1][0] = 0.0
    for mask in range(1 << m):
        for i in range(m):
            if dp[mask][i] == INF:
                continue
            for j in range(m):
                if mask & (1 << j):
                    continue
                v = dp[mask][i] + d[i][j]
                if v < dp[mask | (1 << j)][j]:
                    dp[mask | (1 << j)][j] = v
    full = (1 << m) - 1
    return min(dp[full][i] + d[i][0] for i in range(m))


def brute_force(inst):
    C = list(inst["customers"].keys())
    n = len(C)
    best = [INF]

    def rec_route(route):
        full = [0] + route + [0]
        m = len(full)

        def rec(cur_pos, remaining, trips):
            if not remaining:
                v = X.fstsp_makespan_clean(inst, full, trips)
                if v < best[0]:
                    best[0] = v
                return
            rem = list(remaining)
            opts = [(c,) for c in rem] + [(a, b) for a in rem for b in rem
                                          if a != b]
            for lp in range(cur_pos, m - 1):
                for rp in range(lp + 1, m):
                    ln, rn = full[lp], full[rp]
                    for cs in opts:
                        if any(c not in remaining for c in cs):
                            continue
                        legs = [ln] + list(cs) + [rn]
                        dd = sum(w6.dist(inst, legs[k], legs[k + 1])
                                 for k in range(len(legs) - 1))
                        if dd > X.R_D + 1e-9:
                            continue
                        rec(rp, remaining - set(cs), trips + [(ln, cs, rn)])

        rec(0, set(C) - set(route), [])

    for k in range(n + 1):
        for sub in permutations(C, k):
            rec_route(list(sub))
    return best[0]


@pytest.mark.parametrize("n", [6, 7])
def test_zero_range_reduces_to_truck_only_tsp(n):
    inst = w6.make_instance(n, seed=20260720)
    res = X.solve_exact(inst, max_cust=2, rd=0.0, time_limit=60, num_workers=8)
    tsp = held_karp(inst, list(inst["customers"].keys())) + n * w6.SERVICE
    assert res["proven"]
    assert res["makespan"] == pytest.approx(tsp, abs=0.02)


def test_matches_brute_force_on_tiny_instance():
    inst = w6.make_instance(5, seed=20260720)
    bf = brute_force(inst)
    res = X.solve_exact(inst, max_cust=2, time_limit=60, num_workers=8)
    assert res["proven"]
    assert res["makespan"] == pytest.approx(bf, abs=0.02)


@pytest.mark.parametrize("n", [6, 7])
def test_exact_is_below_clean_greedy(n):
    inst = w6.make_instance(n, seed=20260720)
    res = X.solve_exact(inst, max_cust=2, time_limit=30, num_workers=8)
    gr, gt, _ = X.clean_greedy(inst, max_cust=2)
    # the model's feasible set contains the greedy solution, so the optimum
    # (or the best value found) cannot be above it
    assert res["makespan"] is not None
    assert res["makespan"] <= X.fstsp_makespan_clean(inst, gr, gt) + 1e-6

def test_objective_matches_physical_re_evaluation():
    """The CP-SAT objective is rounded to 1/SC, so the reconstructed plan must
    re-evaluate to it within the discretisation bound. The self-test in
    cpsat_fstsp._main used to compare with a fixed 1e-6 and failed whenever the
    optimum did not sit exactly on the 0.01 grid."""
    inst = w6.make_instance(6, seed=20260720)
    res = X.solve_exact(inst, max_cust=2, time_limit=60, num_workers=8)
    assert res["route"] is not None
    chk = X.fstsp_makespan_clean(inst, res["route"], res["trips"])
    assert math.isfinite(chk)
    assert abs(chk - res["makespan"]) <= X._rounding_tolerance(
        res["route"], res["trips"])
