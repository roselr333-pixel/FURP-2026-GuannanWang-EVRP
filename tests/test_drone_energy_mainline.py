"""The drone energy/payload gates on the two main-line evaluators.

`drone_energy.py` defines the payload/energy model (payload capacity P_MAX plus
an energy budget E_D whose consumption grows with the load still on board). These
tests pin down that the V3 (electric truck + charging + time windows) evaluator
and the FSTSP K-drone evaluator apply that model identically, that their defaults
still reproduce the range-only model, and that the gates reject the plans they
should reject.
"""

import pytest

import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7
import week08_multidrone as M
import v3_ev_collab as v3
import drone_energy as DE

INF = float("inf")
SYNTHETIC = [("synth-n8", w6.make_instance(8, seed=20260720)),
             ("synth-n12", w6.make_instance(12, seed=20260721))]
# the explicit form of the evaluators' defaults: energy budget == range constant
LOOSE = {"alpha": DE.ALPHA, "beta": 0.0, "ed": w6.R_D, "p_max": INF}


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_v3_defaults_are_the_range_only_model(tag, inst):
    """The default keyword arguments must not change the committed evaluator."""
    route, trips, _ = v3.v3_greedy(inst)
    a = v3.ev_collab_k(inst, route, trips, 1)
    b = v3.ev_collab_k(inst, route, trips, 1, **LOOSE)
    for key in ("makespan", "tw_viol", "recharges", "energy_inf",
                "payload_inf", "offloaded", "truck_makespan"):
        assert a[key] == b[key], key


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_v3_payload_cap_binds(tag, inst):
    route, trips, _ = v3.v3_greedy(inst)
    assert trips, "the greedy is expected to offload at least one customer"
    r = v3.ev_collab_k(inst, route, trips, 1, p_max=0.0)
    assert r["payload_inf"] is True
    assert r["makespan"] == INF


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_v3_energy_budget_binds(tag, inst):
    """A plan that is fine under the range model must break once the payload
    coefficient or a tighter energy budget is applied."""
    route, trips, _ = v3.v3_greedy(inst)
    loose = v3.ev_collab_k(inst, route, trips, 1, **LOOSE)
    assert loose["energy_inf"] is False
    assert v3.ev_collab_k(inst, route, trips, 1, beta=10.0)["energy_inf"] is True
    assert v3.ev_collab_k(inst, route, trips, 1, ed=1.0)["energy_inf"] is True


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_v3_greedy_respects_the_energy_model(tag, inst):
    """Run the greedy under the drone_energy defaults: every sortie it builds
    must satisfy the payload cap and the energy budget."""
    kw = {"alpha": DE.ALPHA, "beta": DE.BETA, "ed": DE.E_D, "p_max": DE.P_MAX}
    route, trips, _ = v3.v3_greedy(inst, **kw)
    r = v3.ev_collab_k(inst, route, trips, 1, **kw)
    assert r["energy_inf"] is False
    assert r["payload_inf"] is False
    for _ln, custs, _rn in trips:
        cl = list(custs) if isinstance(custs, (list, tuple)) else [custs]
        assert sum(inst["demand"][c] for c in cl) <= DE.P_MAX + 1e-9


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_fstsp_energy_defaults_reproduce_range_only(tag, inst):
    """The FSTSP evaluators must be unchanged when the gates are left at their
    defaults, for one and for several drones."""
    route, trips, _ = f7.fstsp_insertion(inst)
    base = f7.fstsp_makespan(inst, route, trips)
    assert f7.fstsp_makespan(inst, route, trips, **LOOSE) == pytest.approx(base)
    for K in (1, 2, 3):
        got = f7.fstsp_makespan_multi(inst, route, trips, K, **LOOSE)
        ref = f7.fstsp_makespan_multi(inst, route, trips, K)
        assert got == pytest.approx(ref)


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_fstsp_energy_gates_reject(tag, inst):
    route, trips, _ = f7.fstsp_insertion(inst)
    assert trips, "the published heuristic is expected to use the drone"
    assert f7.fstsp_makespan(inst, route, trips, p_max=0.0) == INF
    assert f7.fstsp_makespan(inst, route, trips, beta=10.0) == INF
    assert f7.fstsp_makespan_multi(inst, route, trips, 2, ed=1.0) == INF
    # a truck-only plan has no sortie, so the gates cannot bite
    truck_only = f7.fstsp_makespan(inst, route, [], p_max=0.0, ed=1.0)
    assert truck_only != INF


@pytest.mark.parametrize("tag,inst", SYNTHETIC)
def test_w8_greedy_respects_the_energy_model(tag, inst):
    kw = {"alpha": DE.ALPHA, "beta": DE.BETA, "ed": DE.E_D, "p_max": DE.P_MAX}
    for K in (1, 2):
        route, trips, off = M.greedy_multi(inst, K, **kw)
        assert f7.fstsp_makespan_multi(inst, route, trips, K, **kw) != INF
        served = sum(len(c) if isinstance(c, (list, tuple)) else 1
                     for _ln, c, _rn in trips)
        assert len(off) == served


def test_energy_gates_agree_between_the_two_evaluators():
    """Both evaluators call the same energy function, so a plan the budget
    rejects must be rejected by the V3 evaluator as well."""
    inst = w6.make_instance(8, seed=20260720)
    route, trips, _ = f7.fstsp_insertion(inst)
    kw = {"alpha": DE.ALPHA, "beta": 10.0, "ed": DE.E_D, "p_max": 1e9}
    assert f7.fstsp_makespan(inst, route, trips, **kw) == INF
    # the V3 evaluator wants each sortie's customers as a tuple
    wrapped = [(ln, (c,) if isinstance(c, int) else tuple(c), rn)
               for ln, c, rn in trips]
    assert v3.ev_collab_k(inst, route, wrapped, 1, **kw)["energy_inf"] is True


def test_sortie_energy_is_the_leg_sum_with_the_load_on_board():
    """Hand-computed check of the energy formula the evaluators share."""
    inst = w6.make_instance(8, seed=20260720)
    c0, c1 = sorted(inst["customers"].keys())[:2]
    alpha, beta = DE.ALPHA, 0.02
    d1 = w6.dist(inst, 0, c0)
    d2 = w6.dist(inst, c0, c1)
    d3 = w6.dist(inst, c1, 0)
    q0 = inst["demand"][c0]
    q1 = inst["demand"][c1]
    want = ((alpha + beta * (q0 + q1)) * d1
            + (alpha + beta * q1) * d2
            + alpha * d3)
    got = DE.sortie_energy(inst, 0, (c0, c1), 0, alpha, beta)
    assert got == pytest.approx(want)
    # and it grows with the payload coefficient
    heavier = DE.sortie_energy(inst, 0, (c0, c1), 0, alpha, beta * 2)
    assert heavier > got
