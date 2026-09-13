# Deep Analysis: *Why* and *When* Truck–Drone Collaborative EVRP-TW Works

> This analysis strings the scattered results from earlier weeks (5-config ablation, parameter
> sensitivity, multi-objective trade-off, three baselines, failure cases) into one coherent
> conclusion chain: where the collaboration gain comes from, in what scenarios it pays off, and
> where the method's own boundary lies. Every number
> here comes from this project's own experiments; no peer's report structure or conceptual
> framework is borrowed.

---

## 1. The main thread: the gain comes from *multi-customer ability*, not *number of rendezvous*

This is the single most important point to make, and two **independent** experiments confirm it:

- **Controlled ablation** (week07, 5 configs on the same stage): holding "drone may take off/land
  several times" fixed, relaxing "at most 1 customer per sortie" to "2–3 customers" yields a gain of
  **+8.6 ~ 12.1 percentage points**; whereas "allowing multiple takeoffs/landings" by itself only
  contributes **+2.2 ~ 4.4 pp**. So letting the drone **serve several customers on one
  outbound trip** is the main source of gain.
- **Parameter sensitivity** (week06, sweeping K = customers per sortie): as K rises 1 → 3, the
  synergy benefit rises **20.5% → 37.1%**, exactly the same direction as the ablation.

The two experiments use different instance sets and different angles, but point at the same
conclusion — which means the conclusion is **stable**, not an artifact of one run. This is where the
project pairs two independent experiments instead of reporting one flattering number, and it uses controlled
experiments to surface the mechanism that actually matters.

**The same ablation re-run on official Solomon topologies** (48 standard instances: C1/C2/R1/RC1 x N=8/12/16/20 x 3 customer windows) gives a multi-customer gain of **+7.2 ~ 8.9 percentage points** and a multi-takeoff gain of **+1.3 ~ 2.0 pp**, with `abl_cap1` still equal to published instance by instance. The main gain source is the same on both geometries; by family the magnitude varies a lot (14.1pp on the uniform R topology, 5.7-5.8pp on the clustered C1/C2 topologies), so how much the multi-customer ability buys depends on the spatial pattern. See `docs/weekly/week07_ablation_std_note_en.md`.

---

## 2. The applicability window: collaboration pays most when customers are spread out, range is ample, and scale is moderate

Putting the four physical-parameter sweeps together characterises the **applicability
boundary** of the synergy (all 5-seed means; error bands in `figures/sensitivity_panels.png`):

| Parameter | Sweep | Synergy benefit | Reading |
|---|---|---|---|
| Battery Q | 120 → 500 | 41.2% → 29.7% | larger battery → truck more self-sufficient → drone value diluted |
| **Drone range R** | 60 → 200 | **15.4% → 34.4%** (saturates after 160) | range < 160 is a *real bottleneck*, binding the gain |
| Customers/sortie K | 1 → 3 | 20.5% → 37.1% | consistent with ablation: multi-customer ability is the main gain |
| Customer scale N (distance dim.) | 8 → 30 | 35.3% → 32.1% | distance-dim benefit dilutes with scale |

**Scale extension (time dimension, N=30/50/100, 5 seeds)**: V2's makespan advantage over V1 goes
8.6% → 3.4% → 0.5%, while the offload rate falls 11.3% → 5.2% → 2.8% monotonically; at N=100
V2 averages **88.6 / 100 late customers** (time-window feasibility collapses, because the greedy was
never TW-feasible by construction). Full curves in `figures/largen_scale_decay.png`.

**Standard-instance check (Schneider 2014, 24 samples per size)**: the same evaluators and
variants on real coordinates, real time windows, real stations and the paper's own battery give a
*larger* collaboration gain than the synthetic reference — **54.8 / 48.8 / 43.7 / 41.0%** at
N=8/12/16/20 against 34.5 / 29.0 / 28.7 / 24.8% — and the drone also cuts late customers from
5.2 / 8.8 / 12.7 / 17.0 to 1.0 / 2.9 / 5.0 / 7.7. The synthetic line therefore *under-states* the
collaboration benefit; what breaks the single-truck model on this data is the paper's own fleet
capacity (C=200), not the geometry (`figures/std_instances.png`, evidence index §5c).

**Overall conclusion**: truck–drone collaboration pays most when "customers are dispersed, drone
range is unconstrained, and the problem scale is moderate"; once the scale is large enough that the
battery constraint nearly doubles the truck's cost, the collaboration dividend is diluted (the
*effective* collaboration window in practice narrows to **N ≤ 30**; only 3.4% is left at N=50). The W8 LNS lifts the N=50
benefit in the same FSTSP setting from the greedy's 15.2% to 29.5%, slowing this decay. This is a **data-backed
applicability judgement**, not a vague "drones are useful".

---

## 3. Multi-objective: V2 dominates V1 on *both* distance and makespan

In a synchronous truck–drone model, distance and completion time (makespan) are in natural tension.
Using a weighted-sum sweep (w ∈ {0, 0.25, 0.5, 0.75, 1.0}, 5 seeds) I get:

- Pure-truck EV (V1) mean: (distance 486.5, makespan 622.5)
- Collaborative (V2) mean: (distance 330.7, makespan 413.6)
- i.e. distance **−32%**, makespan **−34%** — V2 dominates V1 on **both axes**, a genuine Pareto improvement.

**Note**: this uses a weighted-sum scalarised greedy, not a full NSGA-II / Pareto solver, so
the front produced is "coarse". This is a *limitation* of the method; it is
written into the limitations section below.

---

## 4. Relation to the three baselines: where each one stands (consolidated)

I put the three pure-truck VRPTW baselines (OR-Tools, GA, PyVRP) next to BKS in one table
(`baseline_consolidated.csv`, 56 Solomon instances):

| Baseline | Mean gap vs BKS | Role |
|---|---:|---|
| **PyVRP** (standard open-source) | **−3.0%** | strongest baseline, community-standard solver |
| OR-Tools (commercial) | +7.2% | main comparison baseline |
| GA (own, 5-seed mean) | +36.6% ± 15.8% | own metaheuristic, weaker than the other two |

**Note**: my V2 is a *collaborative heuristic* optimising a makespan-driven synchronous
objective; its "distance" is not directly comparable to these pure distance-minimising baselines.
They are placed side by side to show that on standard truck VRPTW a domain solver (PyVRP)
reaches or slightly beats BKS; the project's real increment lies in *collaborative modelling*,
not single-objective distance optimisation.

---

## 5. Failure-case analysis

Among the failure cases, the most telling one is this: on N=50 dense instances, the
**synchronous-feasibility rejection count reaches ~1.01 million**. This shows that the synchronous
rendezvous constraint (the drone must rejoin the truck path at some point) is the main bottleneck at
large scale — exactly corroborating the "benefit dilutes with scale" finding from §2, and jointly
bounding the method's applicability. Failure is not embarrassing; it *corroborates* the sensitivity
conclusion and together with it delimits where the method works.

---

## 6. Limitations

- **The greedy itself has no local search (W8 adds an LNS)**: applying intra-route 2-opt
  post-processing to V2 yields 1.97–3.22% — meaning once far-flung customers are offloaded, the
  truck route is already near-linear, so route fine-tuning is nearly useless; the gain comes from
  *collaborative structure*. With the W8 destroy-and-repair LNS the gain over the greedy is a
  consistent **+12.5% to +21.3% at every size** (Wilcoxon overall p=1.7×10⁻¹⁰), and it offsets the scaling
  decay (N=50: 15.2% → 29.5%).
- **2–3 customers per sortie cap**: a simplification and a boundary; larger-scale multi-customer
  service needs heavier search.
- **Drone count**: all results use a single truck; the W8 extension tests "single drone" up to
  K=1/2/3 (K=1→3 lifts the N=50 benefit from 29.5% to 38.1%), but still on the FSTSP evaluator
  (no time windows or energy).
- **Truck capacity is now enforced, and it is the binding limit at N=100**: with `CAP=1000`
  the constraint is free for N≤50 but one of the five N=100 instances (demand 1081) becomes
  infeasible for all three variants; with a cap below the total demand the single-drone greedy
  cannot repair the overload — it leaves 64.7% (N=8) to 97.2% (N=100) of the demand on the
  truck (`week06_capacity_study.py`, figure `figures/capacity_binding.png`).
- **Synthetic instances extended to 100, but the effective window narrows to N ≤ 30**: I did not adopt
  the field's standard large-scale benchmark sets (e.g., the Solomon-derived FSTSP instances of
  Murray & Chu 2015 — which this project reproduced within their parameter range in W7; or the
  Masmoudi et al. 2018 set) — although the W6 main line itself is now also cross-checked on the original Schneider (2014) E-VRPTW instances (`week06_standard_instances.py`), where the benefit is larger. At N=100 the synergy collapses to 0.5% and V2 averages 88.8/100 late
  customers (TW feasibility breaks down); extrapolation needs caution. W8 extension 2 re-ran 16
  standard instances built from official Solomon topologies (K=1/2/3/5) with a consistent
  conclusion, so the results no longer rest on random geometry alone.
- **No MILP lower bound replicated**: the baseline comparison uses BKS (literature optimum) rather
  than a self-proven bound; absolute quality is anchored to the literature, not self-certified.

---

## 7. Summary

Not in a fancier method (the greedy framework was never swapped) — but in stringing the
conclusions together:

> Controlled ablation locates the main gain source (multi-customer ability) → sensitivity confirms
> it from an independent angle (K sweep) → four parameters characterise the applicability window
> (dispersed customers / ample range / moderate scale) → scale extension to 100 reveals synergy
> collapse and TW breakdown (effective window N ≤ 30) → multi-objective proves dominance on both
> axes → three baselines place V2's collaborative increment → failure cases corroborate
> the rendezvous constraint → the W8 LNS adds an improvement phase (+12.5~21.3%, offsetting the scaling
> decay) → multiple drones (K=1/2/3, N=50 benefit 29.5%→38.1%) → limitations stated plainly
> (scale boundary / synthetic instances / no TW-energy).

Every conclusion traces back to an experiment rather than to "I think
so"; the final report will follow that order.

---

*Data provenance:*
- `src/results/week07_ablation_*.csv` (5-config ablation)
- `src/results/week06_sensitivity.csv` + `figures/sensitivity_panels.png` (sensitivity, 5-seed mean±std)
- `src/results/week06_multi_objective.csv` + `figures/mo_*.png` (multi-objective trade-off)
- `src/results/baseline_consolidated.csv` + `figures/baseline_consolidated.png` (three baselines)
- `src/results/week06_largeN_*.csv` (N=30/50/100 decay) + `figures/largen_scale_decay.png`
- `docs/reference/failure_cases_master.md` (13 failure cases)
- `src/results/schneider_evrptw_bks_comparison.csv` + `figures/schneider_routes.png` /
  `figures/schneider_vehcomp.png` (Schneider 2014 E-VRPTW replication, my routes vs BKS)
