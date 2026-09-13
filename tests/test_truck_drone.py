"""Regression tests for the truck-drone evaluators (W5 v1/v2 and M&C 2015).

The W5 evaluators carried the same physical defect as the FSTSP ones: one drone
is a serial resource, so a sortie may only start once the drone is back on the
truck at its launch node.  The tests below pin that down, check that the truck
waits at a recovery node when the drone lands late, and verify that the two
W5 scripts report the same baselines (they disagreed before the fix).
"""

import math
import random

import pytest

import week05_truck_drone as v1
import week05_truck_drone_v2 as v2
import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import fstsp_mc as M


def _pure_truck_arrivals(route):
    """Truck arrival times for a W5 v2 route, recomputed from the coordinates,
    i.e. without any waiting for the drone."""
    full = [0] + list(route) + [0]
    arr = [0.0] * len(full)
    for p in range(1, len(full)):
        arr[p] = arr[p - 1] + v2.dist(v2.coord(full[p - 1]),
                                      v2.coord(full[p])) / v2.TRUCK_SPEED
        if full[p] != 0:
            arr[p] += v2.SERVICE_TIME
    return full, arr


# --------------------------------------------------------------------------- #
# week05 v2: one drone, serial sorties, truck waits at the recovery node
# --------------------------------------------------------------------------- #
def test_v2_valid_sortie_is_finite_and_needs_no_wait():
    route, trips = [1, 3], [(1, 2, 3)]
    arr, drone_free = v2.simulate(route, trips)
    _, pure = _pure_truck_arrivals(route)
    assert math.isfinite(drone_free)
    assert drone_free <= arr[-1] + 1e-9          # drone is back before the truck
    assert arr[-1] == pytest.approx(pure[-1])     # so nothing waits


def test_v2_rejects_sortie_that_launches_while_drone_is_airborne():
    # the first sortie recovers at the depot, which the truck only reaches at
    # t=289.7, so the drone cannot be launched from node 3 at t=128.3
    route, trips = [1, 3, 5], [(1, 2, 0), (3, 4, 0)]
    arr, drone_free = v2.simulate(route, trips)
    assert drone_free == float("inf")
    assert max(arr[-1], drone_free) == float("inf")


def test_v2_rejects_recovery_before_launch():
    route, trips = [1, 3, 5], [(3, 4, 1)]
    _, drone_free = v2.simulate(route, trips)
    assert drone_free == float("inf")


def test_v2_truck_waits_for_a_late_drone():
    route, trips = [5, 3], [(5, 6, 3)]
    arr, drone_free = v2.simulate(route, trips)
    _, pure = _pure_truck_arrivals(route)
    recovery = 2                                # position of customer 3 in [0,5,3,0]
    assert math.isfinite(drone_free)
    assert drone_free > pure[recovery] + 1e-9   # the drone lands after the truck
    assert arr[recovery] == pytest.approx(drone_free)
    assert arr[recovery] > pure[recovery] + 1e-9  # so the wait was inserted
    assert arr[-1] == pytest.approx(
        arr[recovery] + v2.dist(v2.CUSTOMERS[3], v2.DEPOT))


def test_v2_greedy_plan_is_physically_valid():
    collab, route, trips, _, drone_free = v2.flexible_drone()
    arr, df = v2.simulate(route, trips)
    assert math.isfinite(collab)
    assert df == pytest.approx(drone_free)
    assert collab == pytest.approx(max(arr[-1], df))


# --------------------------------------------------------------------------- #
# cross-module consistency: week05_truck_drone.py vs week05_truck_drone_v2.py
# --------------------------------------------------------------------------- #
def test_v1_and_v2_use_the_same_instance():
    assert v1.CUSTOMERS == v2.CUSTOMERS
    assert v1.DEPOT == v2.DEPOT
    assert v1.TRUCK_SPEED == v2.TRUCK_SPEED
    assert v1.DRONE_SPEED == v2.DRONE_SPEED
    assert v1.SERVICE_TIME == v2.SERVICE_TIME


def test_depot_only_baseline_agrees_across_week05_scripts():
    order = sorted(v1.CUSTOMERS,
                   key=lambda c: -v1.dist(v1.DEPOT, v1.CUSTOMERS[c]))
    drone_set = set(order[: len(order) // 2])
    truck_set = set(order[len(order) // 2:])
    drone_pts = {c: v1.CUSTOMERS[c] for c in drone_set}
    truck_pts = {c: v1.CUSTOMERS[c] for c in truck_set}
    v1_collab = max(v1.makespan(drone_pts, v1.DRONE_SPEED),
                    v1.makespan(truck_pts, v1.TRUCK_SPEED))
    assert v2.depot_only_drone()[0] == pytest.approx(v1_collab)
    # the truck-only reference must agree as well
    assert v2.truck_makespan(v2.nn_tour(v2.CUSTOMERS))[0] == pytest.approx(
        v1.makespan(v1.CUSTOMERS, v1.TRUCK_SPEED))


# --------------------------------------------------------------------------- #
# Murray & Chu (2015) matrix evaluator
# --------------------------------------------------------------------------- #
def _line_instance():
    """0 = start depot, 1..4 = customers, 5 = end depot, all on a line."""
    n = 6
    truck_m = [[float(abs(i - j)) for j in range(n)] for i in range(n)]
    drone_m = [[v / 2.0 for v in row] for row in truck_m]
    return {"customers": [1, 2, 3, 4], "end": 5, "drone_ok": {2, 3, 4},
            "tau": truck_m, "tauprime": drone_m}


def test_mc_greedy_plan_on_a_real_instance_is_physically_valid():
    inst = M.load_mc(M.list_instances()[0])
    route, trips = M.mc_greedy(inst, K=1, max_cust=1)
    makespan = M.mc_simulate(inst, route, trips,
                             inst["tau"], inst["tauprime"], 1)
    assert makespan is not None
    assert math.isfinite(makespan)


def test_mc_accepts_a_valid_sortie():
    inst = _line_instance()
    route = [0, 1, 2, inst["end"]]
    makespan = M.mc_simulate(inst, route, [(1, (3,), inst["end"])],
                             inst["tau"], inst["tauprime"], 1)
    assert makespan is not None
    assert math.isfinite(makespan)


def test_mc_rejects_sortie_that_launches_while_drone_is_airborne():
    inst = _line_instance()
    route = [0, 1, 2, inst["end"]]
    trips = [(1, (3,), inst["end"]), (2, (4,), inst["end"])]
    assert M.mc_simulate(inst, route, trips,
                         inst["tau"], inst["tauprime"], 1) is None


def test_mc_rejects_recovery_before_launch():
    inst = _line_instance()
    route = [0, 1, 2, inst["end"]]
    assert M.mc_simulate(inst, route, [(2, (3,), 1)],
                         inst["tau"], inst["tauprime"], 1) is None


def test_mc_rejects_drone_customer_that_is_not_uav_eligible():
    inst = _line_instance()
    inst["drone_ok"] = {3}
    route = [0, 1, 2, inst["end"]]
    assert M.mc_simulate(inst, route, [(1, (4,), inst["end"])],
                         inst["tau"], inst["tauprime"], 1) is None

# --------------------------------------------------------------------------- #
# cross-module consistency: the M&C matrix evaluator and the shared FSTSP one
# --------------------------------------------------------------------------- #
def _paired_instances(n=8, seed=20260913):
    """The same customers expressed for both evaluators: coordinates for
    week07_fstsp_repro (and week06), time matrices for fstsp_mc."""
    base = w6.make_instance(n, seed=seed)
    ids = [0] + sorted(base["customers"])
    end = max(ids) + 1                       # M&C uses a distinct ending depot
    coord = dict(base["coord"])
    coord[end] = base["depot"]

    def d(a, b):
        ca, cb = coord[a], coord[b]
        return math.hypot(ca[0] - cb[0], ca[1] - cb[1])

    size = end + 1
    tau = [[d(i, j) / f7.V_T for j in range(size)] for i in range(size)]
    taup = [[d(i, j) / f7.V_D for j in range(size)] for i in range(size)]
    inst7 = {"coord": coord, "depot": base["depot"],
             "customers": {i: coord[i] for i in ids[1:]}}
    inst_mc = {"customers": ids[1:], "end": end, "drone_ok": set(ids[1:]),
               "tau": tau, "tauprime": taup}
    return inst7, inst_mc, ids, end


def test_mc_evaluator_matches_shared_fstsp_evaluator_on_random_plans():
    """fstsp_mc.mc_simulate works on M&C time matrices and week07_fstsp_repro
    works on coordinates; on the same instance they must return the same
    makespan and reject exactly the same plans."""
    inst7, inst_mc, ids, end = _paired_instances()
    rng = random.Random(7)
    compared = rejected = 0
    for _ in range(200):
        allc = ids[1:]
        rng.shuffle(allc)
        n_drone = rng.randint(0, min(3, len(allc) - 2))
        drone_c, truck_c = allc[:n_drone], allc[n_drone:]
        route7 = [0] + truck_c + [0]
        trips7 = []
        in_range = True
        for c in drone_c:
            positions = list(range(len(route7) - 1))
            i = rng.choice(positions)
            j = rng.choice([p for p in positions if p > i] or [len(route7) - 1])
            trips7.append((route7[i], c, route7[j]))
            if (w6.dist(inst7, route7[i], c)
                    + w6.dist(inst7, c, route7[j])) > f7.R_D:
                in_range = False
        if not in_range:                      # the range rule exists only in f7
            continue
        route_mc = [0] + truck_c + [end]
        trips_mc = [(ln, (c,), (rn if rn != 0 else end))
                    for (ln, c, rn) in trips7]
        mk7 = f7.fstsp_makespan(inst7, route7, trips7)
        mk_mc = M.mc_simulate(inst_mc, route_mc, trips_mc,
                              inst_mc["tau"], inst_mc["tauprime"], 1,
                              service=f7.SERVICE)
        compared += 1
        if math.isinf(mk7):
            rejected += 1
            assert mk_mc is None
        else:
            assert mk_mc is not None
            assert mk_mc == pytest.approx(mk7, abs=1e-6)
    assert compared > 100                     # the sample is meaningful
    assert rejected > 0                       # and it exercises the rejects
