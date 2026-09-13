"""Schneider (2014) E-VRPTW solver: horizon handling and local search.

The constructive greedy had two latent defects that the local search now depends
on being fixed:

  * the depot's own closing time (the horizon) was only checked when a trip was
    appended to an *existing* vehicle, so the first trip of a new vehicle could
    return after the depot closed (3 of the 18 BKS comparison instances did);
  * the local search needs a station-repair routine that re-checks capacity,
    time windows and battery from scratch.

These tests pin those down, plus the hierarchy of the objective (vehicles first,
distance second) and that no customer is ever lost by a move.
"""

import math
import os

import pytest

import schneider_evrptw as SE
import schneider_improve as SI

SMALL = ["c101C5", "c208C5", "r203C5", "rc204C5"]
LARGE = "c201_21"


def _inst(name):
    return SE.parse_instance(os.path.join(SE.INST_DIR, name + ".txt"))


def _serve_count(inst, routes):
    """routes is vehicle -> trips -> node ids."""
    nodes = SI.nodes_of(inst)
    return [n for veh in routes for rt in veh for n in rt
            if nodes[n]["type"] == "c"]


@pytest.mark.parametrize("name", SMALL + [LARGE])
def test_every_trip_respects_the_depot_horizon(name):
    inst = _inst(name)
    res = SE.solve(inst, improve=False)
    nodes = SI.nodes_of(inst)
    horizon = inst["depot"]["due"]
    for veh in [{"clock": 0.0, "trips": [list(rt) for rt in v]}
                for v in res["routes"]]:
        clock = 0.0
        for rt in veh["trips"]:
            ok, _d, clock = SI.eval_route(inst, rt, clock, nodes)
            assert ok, f"{name}: trip is infeasible from scratch"
            assert clock <= horizon + 1e-6, f"{name}: trip ends after the depot closes"


@pytest.mark.parametrize("name", SMALL)
def test_local_search_improves_or_keeps_the_hierarchical_key(name):
    inst = _inst(name)
    base = SE.solve(inst, improve=False)
    imp = SE.solve(inst, improve=True)
    assert (imp["vehicles"], imp["distance"]) <= (base["vehicles"],
                                                  base["distance"])
    assert imp["distance"] <= base["distance"] + 1e-9 or \
        imp["vehicles"] < base["vehicles"]
    assert imp["constructive_vehicles"] == base["vehicles"]


@pytest.mark.parametrize("name", SMALL)
def test_nothing_is_lost_or_duplicated(name):
    inst = _inst(name)
    res = SE.solve(inst, improve=True)
    served = _serve_count(inst, res["routes"])
    assert len(served) == len(set(served)) == len(inst["customers"])


def test_improved_solution_is_physically_feasible():
    inst = _inst(LARGE)
    res = SE.solve(inst, improve=True, improve_moves=25, improve_budget=20.0)
    nodes = SI.nodes_of(inst)
    for veh in [{"clock": 0.0, "trips": [list(rt) for rt in v]}
                for v in res["routes"]]:
        clock = 0.0
        for rt in veh["trips"]:
            ok, _d, clock = SI.eval_route(inst, rt, clock, nodes)
            assert ok


def test_repair_route_inserts_the_cheapest_station():
    """A hand-built instance: the direct leg is out of battery and two stations
    are reachable; the cheaper detour must be chosen and the distance accounting
    must equal a manual sum."""
    inst = {
        "depot": {"id": "D0", "type": "d", "x": 0.0, "y": 0.0,
                  "demand": 0.0, "ready": 0.0, "due": 10000.0, "serv": 0.0},
        "stations": [
            {"id": "S1", "type": "f", "x": 45.0, "y": 0.0, "demand": 0.0,
             "ready": 0.0, "due": 10000.0, "serv": 0.0},
            {"id": "S2", "type": "f", "x": 42.0, "y": 0.0, "demand": 0.0,
             "ready": 0.0, "due": 10000.0, "serv": 0.0},
        ],
        "customers": [
            {"id": "C1", "type": "c", "x": 40.0, "y": 0.0, "demand": 10.0,
             "ready": 0.0, "due": 10000.0, "serv": 90.0},
        ],
        "params": {"Q": 79.69, "C": 200.0, "r": 1.0, "g": 3.39, "v": 1.0},
    }
    fixed, d, _t = SI.repair_route(inst, ["D0", "C1", "D0"])
    assert fixed is not None
    assert fixed == ["D0", "C1", "S2", "D0"]          # S2 is the cheaper detour
    manual = SI.dist(inst["depot"], inst["customers"][0]) \
        + SI.dist(inst["customers"][0], inst["stations"][1]) \
        + SI.dist(inst["stations"][1], inst["depot"])
    assert d == pytest.approx(manual)


def test_repair_route_returns_none_when_unreachable():
    inst = {
        "depot": {"id": "D0", "type": "d", "x": 0.0, "y": 0.0, "demand": 0.0,
                  "ready": 0.0, "due": 10000.0, "serv": 0.0},
        "stations": [],
        "customers": [
            {"id": "C1", "type": "c", "x": 500.0, "y": 0.0, "demand": 10.0,
             "ready": 0.0, "due": 10000.0, "serv": 90.0},
        ],
        "params": {"Q": 79.69, "C": 200.0, "r": 1.0, "g": 3.39, "v": 1.0},
    }
    fixed, d, _t = SI.repair_route(inst, ["D0", "C1", "D0"])
    assert fixed is None
    assert math.isinf(d)


def test_time_window_violation_is_rejected():
    inst = {
        "depot": {"id": "D0", "type": "d", "x": 0.0, "y": 0.0, "demand": 0.0,
                  "ready": 0.0, "due": 10000.0, "serv": 0.0},
        "stations": [],
        "customers": [
            {"id": "C1", "type": "c", "x": 10.0, "y": 0.0, "demand": 10.0,
             "ready": 0.0, "due": 5.0, "serv": 90.0},
        ],
        "params": {"Q": 79.69, "C": 200.0, "r": 1.0, "g": 3.39, "v": 1.0},
    }
    ok, _d, _t = SI.eval_route(inst, ["D0", "C1", "D0"])
    assert not ok
