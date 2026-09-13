"""The standard-instance adapter for the ground-air EVRP-TW model.

The W6 line is built on random geometry; these tests pin down the mapping from
the original Schneider (2014) E-VRPTW files onto the W6 instance dictionary
(coordinates, time windows, service, battery, recharge, capacity, drone range)
and that the resulting instance runs through the unchanged evaluators.
"""

import math

import pytest

import std_evrp_instances as SI
import week06_ground_air_evrp_tw as w6

NAME = "c101_21"


def _raw():
    return SI.load(NAME)


def test_adapter_maps_the_paper_fields():
    inst, meta = SI.make_evrp(NAME, n=12, start=0, cap_mode="file")
    raw = _raw()
    customers = sorted(raw["customers"], key=SI.node_number)[:12]
    for i, c in enumerate(customers, start=1):
        assert inst["coord"][i] == (c["x"], c["y"])
        assert inst["demand"][i] == c["demand"]
        assert inst["tw"][i] == (c["ready"], c["due"])
    assert inst["depot"] == (raw["depot"]["x"], raw["depot"]["y"])
    assert len(inst["stations"]) == len(raw["stations"])
    p = raw["params"]
    assert inst["Q"] == pytest.approx(p["Q"] / p["r"])
    assert inst["recharge"] == pytest.approx(p["Q"] * p["g"])
    assert inst["service"] == pytest.approx(customers[0]["serv"])
    assert inst["cap"] == pytest.approx(p["C"])
    assert inst["n"] == 12
    assert meta["total_demand"] == pytest.approx(
        sum(c["demand"] for c in customers))


def test_capacity_mode_only_changes_the_cap():
    file_inst, _ = SI.make_evrp(NAME, n=12, cap_mode="file")
    model_inst, _ = SI.make_evrp(NAME, n=12, cap_mode="model")
    assert file_inst["cap"] != model_inst["cap"]
    assert model_inst["cap"] == w6.CAP
    for key in file_inst:
        if key == "cap":
            continue
        assert file_inst[key] == model_inst[key]


def test_drone_range_follows_the_instance_scale():
    inst, meta = SI.make_evrp(NAME, n=12)
    distances = [w6.dist(inst, 0, i) for i in inst["customers"]]
    expected = SI.DRONE_RANGE_FACTOR * sum(distances) / len(distances)
    assert inst["drone_range"] == pytest.approx(expected)
    assert meta["drone_range"] == pytest.approx(expected)
    # much smaller than the synthetic default: the instance is ~100 km across
    assert inst["drone_range"] < w6.R_D / 2


def test_subsets_are_contiguous_blocks_of_the_sorted_customers():
    inst0, _ = SI.make_evrp(NAME, n=8, start=0)
    inst1, _ = SI.make_evrp(NAME, n=8, start=10)
    assert inst0["coord"][1] != inst1["coord"][1]
    raw = _raw()
    ordered = sorted(raw["customers"], key=SI.node_number)
    assert inst1["coord"][1] == (ordered[10]["x"], ordered[10]["y"])


def test_standard_instance_runs_through_the_w6_evaluator():
    inst, meta = SI.make_evrp(NAME, n=12, cap_mode="model")
    for kind in ("V0", "V1", "V2"):
        res = w6.run_variant(inst, kind)
        assert math.isfinite(res["makespan"])
        assert res["feasible"] is True
    v2 = w6.run_variant(inst, "V2")
    assert v2["offloaded"] >= 1
    assert v2["makespan"] < w6.run_variant(inst, "V1")["makespan"]


def test_paper_capacity_binds_for_a_large_subset():
    """C = 200 and ~15 demand per customer: 20 customers no longer fit on one
    truck, which is exactly the single-vehicle-vs-fleet boundary."""
    inst, meta = SI.make_evrp(NAME, n=20, cap_mode="file")
    assert meta["total_demand"] > meta["cap"]
    assert w6.run_variant(inst, "V1")["feasible"] is False
    assert w6.run_variant(inst, "V1")["cap_viol"] == 1


def test_service_time_is_honoured():
    inst, _ = SI.make_evrp(NAME, n=12)
    slow = {**inst, "service": inst["service"] * 2.0}
    fast = {**inst, "service": inst["service"] / 2.0}
    assert (w6.run_variant(slow, "V1")["makespan"]
            > w6.run_variant(fast, "V1")["makespan"])
    assert (w6.run_variant(slow, "V2")["makespan"]
            > w6.run_variant(fast, "V2")["makespan"])


def test_instance_drone_range_is_used_by_the_search():
    inst, _ = SI.make_evrp(NAME, n=12)
    near = {**inst, "drone_range": 1.0}          # nothing reachable
    assert w6.collaborative(near)["offloaded"] == 0
    assert w6.collaborative(inst)["offloaded"] >= 1


def test_all_families_load():
    for fam in SI.FAMILIES:
        inst, meta = SI.make_evrp(f"{fam}_21", n=8)
        assert inst["n"] == 8
        assert len(inst["stations"]) > 0
        assert meta["family"] == fam
