"""Truck capacity (CAP) enforcement in the ground-air EVRP-TW model.

`CAP` used to be declared-but-unchecked, which made every published W6/V3 number
a capacity-free result. These tests pin the behaviour down: an overloaded truck
route is infeasible, the collaborative greedy repairs a mild overload by
offloading, a severe overload stays infeasible (reported, not silently ignored),
and the declared CAP=1000 remains free at the published sizes.
"""

import math

import pytest

import week06_ground_air_evrp_tw as w6

# total demand on this instance is 214 (N=20, seed 20260720)
INST = w6.make_instance(20, seed=20260720)
TOTAL = sum(INST["demand"].values())


def test_truck_load_counts_customers_only():
    inst = w6.make_instance(8, seed=20260720)
    route = [0] + list(inst["customers"].keys()) + list(inst["stations"]) + [0]
    assert w6.truck_load(inst, route) == sum(inst["demand"].values())


def test_route_over_capacity_is_infeasible():
    inst = {**INST, "cap": TOTAL - 1}
    r = w6.truck_ev_route(inst, list(inst["customers"]), allow_recharge=True)
    assert r["cap_inf"] is True
    assert math.isinf(r["makespan"])
    assert r["truck_load"] == TOTAL


def test_route_at_capacity_is_feasible():
    inst = {**INST, "cap": TOTAL}
    r = w6.truck_ev_route(inst, list(inst["customers"]), allow_recharge=True)
    assert r["cap_inf"] is False
    assert math.isfinite(r["makespan"])


def test_simulate_rejects_an_overloaded_truck_route():
    route = [0] + list(INST["customers"].keys()) + [0]
    tight = {**INST, "cap": TOTAL - 1}
    assert math.isinf(w6.simulate(tight, route, [])[1])
    # the search needs to measure partial repairs, so it can switch the check off
    assert math.isfinite(w6.simulate(tight, route, [], check_cap=False)[1])


def test_collaborative_repairs_a_mild_overload():
    cap = TOTAL - 14                      # one or two offloads are enough
    r = w6.collaborative(INST, cap=cap)
    assert r["cap_inf"] is False
    assert r["plan_valid"] is True
    assert r["truck_load"] <= cap
    assert math.isfinite(r["makespan"])


def test_collaborative_reports_a_severe_overload_as_infeasible():
    cap = 50                              # far below what one drone can remove
    r = w6.collaborative(INST, cap=cap)
    assert r["cap_inf"] is True
    assert r["plan_valid"] is False
    assert math.isinf(r["makespan"])


def test_run_variant_reports_capacity_violations():
    inst = {**INST, "cap": TOTAL - 1}
    for kind in ("V0", "V1"):
        res = w6.run_variant(inst, kind)
        assert res["feasible"] is False
        assert res["cap_viol"] == 1
    # the collaborative variant can repair a one-unit overload with a single
    # offload, so it stays feasible and reports no violation
    v2 = w6.run_variant(inst, "V2")
    assert v2["feasible"] is True
    assert v2["cap_viol"] == 0
    assert v2["truck_load"] <= TOTAL - 1


@pytest.mark.parametrize("n", [8, 12, 16, 20])
def test_declared_cap_is_free_at_the_published_sizes(n):
    """The published W6/V3 headline numbers are computed at CAP=1000; at the
    sizes they use the constraint must not bind, otherwise those numbers would
    silently be capacity-constrained results."""
    inst = w6.make_instance(n, seed=20260720)
    assert sum(inst["demand"].values()) <= inst["cap"]
    for kind in ("V0", "V1", "V2"):
        res = w6.run_variant(inst, kind)
        assert res["cap_viol"] == 0
        assert res["feasible"] is True


def test_unlimited_cap_reproduces_the_declared_cap_when_free():
    r_declared = w6.collaborative(INST)
    r_unlimited = w6.collaborative({**INST, "cap": 10 ** 9}, cap=10 ** 9)
    assert r_declared["makespan"] == pytest.approx(r_unlimited["makespan"])
    assert r_declared["offloaded"] == r_unlimited["offloaded"]
