"""Invariants of the ALNS module (physical FSTSP model).

The ALNS is validated the same way as the other search modules: it must serve
every customer exactly once, never return a physically invalid plan, never come
back worse than the solution it started from, and be deterministic for a fixed
seed and iteration budget. The destroy/repair operators are checked for the two
properties the search relies on: a destroyed customer really leaves the plan, and
the repair puts every removed customer back.
"""

import random

import pytest

import week06_ground_air_evrp_tw as w6
import cpsat_fstsp as X
import alns_fstsp as A

INF = float("inf")
INST = [("synth-n8", w6.make_instance(8, seed=20260720)),
        ("synth-n10", w6.make_instance(10, seed=20260721))]


def _served(inst, route, trips):
    served = [c for c in route if c != 0]
    for _ln, custs, _rn in trips:
        served.extend(custs)
    return sorted(served)


@pytest.mark.parametrize("tag,inst", INST)
def test_alns_serves_every_customer_exactly_once(tag, inst):
    route, trips, mk, _iters, _hist = A.alns(inst, seed=1, iters=200)
    assert mk != INF
    assert _served(inst, route, trips) == sorted(inst["customers"].keys())
    assert X.fstsp_makespan_clean(inst, route, trips) == pytest.approx(mk,
                                                                      abs=1e-6)


@pytest.mark.parametrize("tag,inst", INST)
def test_alns_never_worse_than_its_start(tag, inst):
    gr, gt, _ = X.clean_greedy(inst, max_cust=2)
    mk0 = X.fstsp_makespan_clean(inst, gr, gt)
    _r, _t, mk, _iters, _hist = A.alns(inst, seed=2, iters=200)
    assert mk <= mk0 + 1e-9


def test_alns_is_deterministic():
    inst = w6.make_instance(8, seed=20260720)
    a = A.alns(inst, seed=7, iters=150)
    b = A.alns(inst, seed=7, iters=150)
    assert a[2] == b[2]
    assert a[0] == b[0] and list(a[1]) == list(b[1])


def test_alns_improves_a_greedy_start():
    """On an instance where the greedy is far from optimal the search must
    actually move: this is the property that motivates the module."""
    inst = w6.make_instance(12, seed=20260720)
    gr, gt, _ = X.clean_greedy(inst, max_cust=2)
    mk0 = X.fstsp_makespan_clean(inst, gr, gt)
    _r, _t, mk, _iters, _hist = A.alns(inst, seed=3, iters=400)
    assert mk < mk0


@pytest.mark.parametrize("op", A.DESTROY_OPS)
def test_destroy_operators_remove_what_they_report(op):
    inst = w6.make_instance(8, seed=20260720)
    gr, gt, _ = X.clean_greedy(inst, max_cust=2)
    before = set(_served(inst, gr, gt))
    r2, t2, removed = A.DESTROY[op](inst, gr, gt, 3, random.Random(0))
    assert removed, op
    after = set(_served(inst, r2, t2))
    assert removed.isdisjoint(after), op      # reported customers are gone
    assert after <= before, op                # and nothing new appears


@pytest.mark.parametrize("rop", A.REPAIR_OPS)
def test_repair_restores_every_customer(rop):
    inst = w6.make_instance(8, seed=20260721)
    gr, gt, _ = X.clean_greedy(inst, max_cust=2)
    r2, t2, removed = A.d_related(inst, gr, gt, 4, random.Random(1))
    assert removed
    r3, t3 = A.REPAIR[rop](inst, r2, t2, list(removed), random.Random(2))
    assert _served(inst, r3, t3) == sorted(inst["customers"].keys())
    assert X.fstsp_makespan_clean(inst, r3, t3) != INF


@pytest.mark.parametrize("rop", A.REPAIR_OPS)
def test_repair_keeps_the_plan_physically_valid(rop):
    """The repair may not produce overlapping sorties: the clean evaluator is the
    referee, exactly as in the ALNS loop."""
    inst = w6.make_instance(10, seed=20260720)
    gr, gt, _ = X.clean_greedy(inst, max_cust=2)
    mk0 = X.fstsp_makespan_clean(inst, gr, gt)
    r2, t2, removed = A.d_segment(inst, gr, gt, 3, random.Random(5))
    r3, t3 = A.REPAIR[rop](inst, r2, t2, list(removed), random.Random(6))
    mk = X.fstsp_makespan_clean(inst, r3, t3)
    assert mk != INF
    assert mk < INF and mk0 < INF


def test_adaptive_and_fixed_runs_are_both_feasible():
    inst = w6.make_instance(10, seed=20260722)
    for adaptive in (True, False):
        route, trips, mk, _it, _h = A.alns(inst, seed=4, iters=200,
                                           adaptive=adaptive)
        assert mk != INF
        assert _served(inst, route, trips) == sorted(inst["customers"].keys())
