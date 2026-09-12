"""Invariants of the completion-time evaluators.

These guard the properties the reports rely on: the K-drone evaluator must
collapse to the single-drone one at K=1, adding drones must never hurt, and the
V3 (electric + time-window) evaluator must agree with its single-drone form and
still serve every customer.
"""

import pytest

import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab
import fstsp_instances as fi
import v3_ev_collab as v3

SYNTHETIC = [("synth-n10", w6.make_instance(10, seed=20260720)),
             ("synth-n12", w6.make_instance(12, seed=20260721))]
SOLOMON = [("C101-n10", fi.make_solomon_fstsp("C101", 10)),
           ("R101-n10", fi.make_solomon_fstsp("R101", 10))]


@pytest.mark.parametrize("tag,inst", SYNTHETIC + SOLOMON)
def test_k1_multi_equals_single_drone(tag, inst):
    """fstsp_makespan_multi(..., K=1) must equal the single-drone evaluator."""
    route, trips, _ = ab.my_v2_param(inst, max_cust=2, multi_takeoff=True)
    assert f7.fstsp_makespan_multi(inst, route, trips, 1) == pytest.approx(
        f7.fstsp_makespan(inst, route, trips))


@pytest.mark.parametrize("tag,inst", SYNTHETIC + SOLOMON)
def test_more_drones_do_not_hurt(tag, inst):
    """A second drone cannot make the completion time worse."""
    route, trips, _ = ab.my_v2_param(inst, max_cust=2, multi_takeoff=True)
    mk1 = f7.fstsp_makespan_multi(inst, route, trips, 1)
    mk3 = f7.fstsp_makespan_multi(inst, route, trips, 3)
    assert mk3 <= mk1 + 1e-9


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_v3_k1_equals_single_drone(tag, inst):
    """v3.ev_collab is the K=1 special case of ev_collab_k."""
    route, trips, _ = v3.v3_greedy(inst)
    a = v3.ev_collab(inst, route, trips)
    b = v3.ev_collab_k(inst, route, trips, 1)
    assert a["makespan"] == pytest.approx(b["makespan"])
    assert a["tw_viol"] == b["tw_viol"]
    assert a["recharges"] == b["recharges"]


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_v3_serves_every_customer(tag, inst):
    """Truck route plus drone sorties must cover exactly the customer set."""
    route, trips, _ = v3.v3_greedy(inst)
    served = {x for x in route if x != 0}
    for _, custs, _ in trips:
        served.update(custs)
    assert served == set(inst["customers"].keys())


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_v3_energy_feasible_on_greedy_solution(tag, inst):
    """The greedy V3 solution stays energy-feasible (no infeasible recharge)."""
    route, trips, _ = v3.v3_greedy(inst)
    assert v3.ev_collab(inst, route, trips)["energy_inf"] is False
