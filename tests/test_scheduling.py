"""Invariants of the drone-to-sortie scheduler.

The optimised-scheduling report claims the naive "earliest-available" rule is
near-optimal. Three properties make that claim checkable:

  * the naive rule must reproduce the shared multi-drone simulator exactly;
  * greedy >= local >= optimal on every instance (local only improves, optimal
    is the exact minimum);
  * the lower-bound certificate must never exceed the true optimum.
"""

import pytest

import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab
import drone_scheduling as S
import fstsp_instances as fi

CASES = [("synth-n10", w6.make_instance(10, seed=20260720)),
         ("synth-n12", w6.make_instance(12, seed=20260721)),
         ("C101-n10", fi.make_solomon_fstsp("C101", 10)),
         ("R101-n10", fi.make_solomon_fstsp("R101", 10))]


@pytest.mark.parametrize("tag,inst", CASES)
@pytest.mark.parametrize("K", [1, 2, 3])
def test_naive_rule_matches_reference_simulator(tag, inst, K):
    route, trips, _ = ab.my_v2_param(inst, max_cust=2, multi_takeoff=True)
    _, greedy = S.schedule_greedy(inst, route, trips, K)
    assert greedy == pytest.approx(
        f7.fstsp_makespan_multi(inst, route, trips, K))


@pytest.mark.parametrize("tag,inst", CASES)
@pytest.mark.parametrize("K", [1, 2, 3])
def test_scheduler_ordering(tag, inst, K):
    route, trips, _ = ab.my_v2_param(inst, max_cust=2, multi_takeoff=True)
    _, greedy = S.schedule_greedy(inst, route, trips, K)
    _, local = S.schedule_local(inst, route, trips, K)
    _, optimal, _ = S.schedule_optimal(inst, route, trips, K)
    assert greedy >= local - 1e-9
    assert local >= optimal - 1e-9


@pytest.mark.parametrize("tag,inst", CASES)
@pytest.mark.parametrize("K", [1, 2, 3])
def test_lower_bound_is_valid(tag, inst, K):
    route, trips, _ = ab.my_v2_param(inst, max_cust=2, multi_takeoff=True)
    _, greedy = S.schedule_greedy(inst, route, trips, K)
    _, optimal, _ = S.schedule_optimal(inst, route, trips, K)
    lb = S.schedule_lb(inst, route, trips, K)
    assert lb <= optimal + 1e-9
    assert lb <= greedy + 1e-9
