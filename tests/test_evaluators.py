"""Invariants of the completion-time evaluators.

These guard the properties the reports rely on: the K-drone evaluator must
collapse to the single-drone one at K=1, adding drones must never hurt, and the
V3 (electric + time-window) evaluator must agree with its single-drone form and
still serve every customer.
"""

import math
import random

import pytest

import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab
import fstsp_instances as fi
import cpsat_fstsp as X
import v3_ev_collab as v3

SYNTHETIC = [("synth-n10", w6.make_instance(10, seed=20260720)),
             ("synth-n12", w6.make_instance(12, seed=20260721))]
SOLOMON = [("C101-n10", fi.make_solomon_fstsp("C101", 10)),
           ("R101-n10", fi.make_solomon_fstsp("R101", 10))]


@pytest.mark.parametrize("tag,inst", SYNTHETIC + SOLOMON)
def test_heuristic_plans_are_physically_valid(tag, inst):
    """The shared evaluator must agree with the physical evaluator: the greedy
    and the published heuristic must not rely on un-realizable (nested) sortie
    sets, i.e. their makespan must be finite and equal to clean evaluation."""
    plans = [ab.my_v2_param(inst, max_cust=2, multi_takeoff=True),
             ab.my_v2_param(inst, max_cust=1, multi_takeoff=True),
             f7.fstsp_insertion(inst)]
    for route, trips, _ in plans:
        mk = f7.fstsp_makespan(inst, route, trips)
        assert mk != float("inf")
        assert mk == pytest.approx(
            X.fstsp_makespan_clean(inst, route, trips))


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

def _line_instance():
    """Four customers on a line from the depot: every time is exact."""
    coord = {0: (0.0, 0.0), 1: (10.0, 0.0), 2: (20.0, 0.0),
             3: (30.0, 0.0), 4: (40.0, 0.0), 5: (-45.0, 0.0)}
    return {"depot": coord[0],
            "customers": {i: coord[i] for i in (1, 2, 3, 4)},
            "stations": {5: coord[5]},
            "tw": {i: (0.0, 1e9) for i in (1, 2, 3, 4)},
            "demand": {i: 5 for i in (1, 2, 3, 4)},
            "coord": coord, "Q": w6.Q_DEFAULT, "n": 4}


def test_w6_evaluator_rejects_overlapping_sorties():
    """One drone cannot fly two sorties that overlap in time."""
    inst = _line_instance()
    route = [0, 1, 2, 3, 4, 0]
    a = (1, (2,), 3)
    b = (2, (3,), 4)
    assert not math.isinf(w6.simulate(inst, route, [a])[1])
    assert not math.isinf(w6.simulate(inst, route, [b])[1])
    assert math.isinf(w6.simulate(inst, route, [a, b])[1])
    assert math.isinf(w6.simulate(inst, route, [b, a])[1])


def test_w6_evaluator_rejects_out_of_range_sortie():
    """A flight longer than the range is not a plan."""
    inst = _line_instance()
    route = [0, 1, 2, 3, 4, 0]
    trip = (1, (4,), 0)          # 1 -> 4 -> 0 covers 70 length units
    assert math.isinf(w6.simulate(inst, route, [trip], rd=50.0)[1])
    assert not math.isinf(w6.simulate(inst, route, [trip], rd=100.0)[1])


def test_w6_truck_waits_for_a_late_drone():
    """The truck waits at the recovery node and later arrivals shift with it."""
    inst = _line_instance()
    route = [0, 1, 2, 3, 4, 0]
    trip = (1, (4,), 2)          # lands at t=55, the truck is there at t=40
    arr, drone = w6.simulate(inst, route, [trip], rd=100.0)
    assert drone == pytest.approx(55.0)
    assert arr[-1] == pytest.approx(135.0)


def test_w6_evaluator_matches_shared_fstsp_evaluator():
    """week06.simulate and week07.fstsp_simulate are one physical model."""
    rng = random.Random(11)
    for trial in range(60):
        inst = w6.make_instance(rng.choice([8, 10, 12]), seed=4000 + trial)
        cust = list(inst["customers"].keys())
        rng.shuffle(cust)
        route = [0] + cust + [0]
        trips = []
        for _ in range(rng.randint(0, 3)):
            i = rng.randrange(0, len(route) - 2)
            j = rng.randrange(i + 1, len(route) - 1)
            custs = tuple(rng.sample(cust, rng.choice([1, 2])))
            trips.append((route[i], custs, route[j]))
        arr, drone = w6.simulate(inst, route, trips)
        mk = max(arr[-1], drone)
        ref = f7.fstsp_simulate(inst, route, trips)[-1]
        if math.isinf(ref):
            assert math.isinf(mk)
        else:
            assert mk == pytest.approx(ref)


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_w6_collaborative_plan_is_physically_executable(tag, inst):
    """The week06 greedy never returns a plan the evaluator would reject."""
    r = w6.collaborative(inst)
    assert r["plan_valid"] is True
    assert not math.isinf(
        w6.simulate(inst, r["route"], r["drone_trips"], w6.R_D)[1])

def test_fstsp_evaluator_matches_clean_model_on_random_plans():
    """week07.fstsp_simulate and cpsat_fstsp.fstsp_makespan_clean are one model."""
    rng = random.Random(3)
    for trial in range(40):
        inst = w6.make_instance(rng.choice([8, 10, 12]), seed=5000 + trial)
        cust = list(inst["customers"].keys())
        rng.shuffle(cust)
        route = [0] + cust + [0]
        trips = []
        for _ in range(rng.randint(0, 3)):
            i = rng.randrange(0, len(route) - 2)
            j = rng.randrange(i + 1, len(route) - 1)
            custs = tuple(rng.sample(cust, rng.choice([1, 2])))
            trips.append((route[i], custs, route[j]))
        ref = f7.fstsp_makespan(inst, route, trips)
        clean = X.fstsp_makespan_clean(inst, route, trips)
        if math.isinf(clean):
            assert math.isinf(ref)
        else:
            assert ref == pytest.approx(clean)


