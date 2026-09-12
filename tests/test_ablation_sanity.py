"""The W7 ablation sanity check, as an assertion.

The ablation claims the only difference between my V2 method and the published
Murray & Chu (2015) heuristic is the multi-customer capability: run my
framework with max_cust=1 and multi-takeoff on, and it should reproduce the
published baseline exactly. If that ever breaks, the whole gain decomposition
(multi-customer / multi-takeoff) is meaningless, so it is guarded by a hard test.
"""

import pytest

import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week07_improvement_ablation as ab
import fstsp_instances as fi

CASES = [("synth-n10", w6.make_instance(10, seed=20260720)),
         ("synth-n12", w6.make_instance(12, seed=20260721)),
         ("C101-n10", fi.make_solomon_fstsp("C101", 10)),
         ("R101-n10", fi.make_solomon_fstsp("R101", 10)),
         ("C201-n12", fi.make_solomon_fstsp("C201", 12)),
         ("RC101-n16", fi.make_solomon_fstsp("RC101", 16)),
         ("R101-n12-w1", fi.make_solomon_fstsp("R101", 12, start=12))]


@pytest.mark.parametrize("tag,inst", CASES)
def test_abl_cap1_reproduces_published_baseline(tag, inst):
    pub_route, pub_trips, _ = f7.fstsp_insertion(inst)
    ab_route, ab_trips, _ = ab.my_v2_param(inst, max_cust=1,
                                           multi_takeoff=True)
    assert f7.fstsp_makespan(inst, ab_route, ab_trips) == pytest.approx(
        f7.fstsp_makespan(inst, pub_route, pub_trips))
