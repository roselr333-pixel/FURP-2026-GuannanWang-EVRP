# Deep Analysis: *Why* and *When* Truck–Drone Collaborative EVRP-TW Works

> This document is not another experiment checklist. It strings the scattered results from
> earlier weeks (5-config ablation, parameter sensitivity, multi-objective trade-off, three
> baselines, failure cases) into one **defensible conclusion chain**.
> The single purpose is to give the project *depth*: to show where the collaboration gain comes
> from, in what scenarios it pays off, and where the method's own boundary lies. Every number
> here comes from this project's own experiments; no peer's report structure or conceptual
> framework is borrowed.

---

## 1. The main thread: the gain comes from *multi-customer ability*, not *number of rendezvous*

This is the single most important point to make, and two **independent** experiments confirm it:

- **Controlled ablation** (week07, 5 configs on the same stage): holding "drone may take off/land
  several times" fixed, relaxing "at most 1 customer per sortie" to "2–3 customers" yields a gain of
  **+6.6 ~ 17.7 percentage points**; whereas "allowing multiple takeoffs/landings" by itself only
  contributes **+4.1 ~ 7.3 pp**. In other words, letting the drone **serve several customers on one
  outbound trip** is the main source of gain.
- **Parameter sensitivity** (week06, sweeping K = customers per sortie): as K rises 1 → 3, the
  synergy benefit rises **25.3% → 56.5%**, exactly the same direction as the ablation.

The two experiments use different instance sets and different angles, but point at the same
conclusion — which means the conclusion is **stable**, not an artifact of one run. This is where the
project earns its "depth": instead of reporting one flattering final number, it uses controlled
experiments to surface the mechanism that actually matters.

---

## 2. The applicability window: collaboration pays most when customers are spread out, range is ample, and scale is moderate

Putting the four physical-parameter sweeps together lets us characterise the **applicability
boundary** of the synergy (all 5-seed means; error bands in `figures/sensitivity_panels.png`):

| Parameter | Sweep | Synergy benefit | Reading |
|---|---|---|---|
| Battery Q | 120 → 500 | 55.8% → 47.1% | larger battery → truck more self-sufficient → drone value diluted |
| **Drone range R** | 60 → 200 | **15.5% → 50.5%** (saturates after 160) | range < 160 is a *real bottleneck*, binding the gain |
| Customers/sortie K | 1 → 3 | 25.3% → 56.5% | consistent with ablation: multi-customer ability is the main gain |
| Customer scale N (distance dim.) | 8 → 30 | 63.8% → 35.3% | distance-dim benefit dilutes with scale |

**Scale extension (time dimension, N=30/50/100, 5 seeds)**: V2's makespan advantage over V1 goes
27.6% → 12.1% → 2.3%, while the offload rate falls 62.0% → 42.8% → 23.4% monotonically; at N=100
V2 averages **71.4 / 100 late customers** (time-window feasibility collapses, because the greedy was
never TW-feasible by construction). Full curves in `figures/largen_scale_decay.png`.

**Overall conclusion**: truck–drone collaboration pays most when "customers are dispersed, drone
range is unconstrained, and the problem scale is moderate"; once the scale is large enough that the
battery constraint nearly doubles the truck's cost, the collaboration dividend is diluted (the
*effective* collaboration window in practice lies at **N ≤ 50**). This is a **data-backed
applicability judgement**, not a vague "drones are useful".

---

## 3. Multi-objective: V2 dominates V1 on *both* distance and makespan

In a synchronous truck–drone model, distance and completion time (makespan) are in natural tension.
Using a weighted-sum sweep (w ∈ {0, 0.25, 0.5, 0.75, 1.0}, 5 seeds) we get:

- Pure-truck EV (V1) mean: (distance 486.4, makespan 622.4)
- Collaborative (V2) mean: (distance 215.2, makespan 415.7)
- i.e. distance **−56%**, makespan **−33%** — V2 dominates V1 on **both axes**, a genuine Pareto improvement.

**Honest note**: this uses a weighted-sum scalarised greedy, not a full NSGA-II / Pareto solver, so
the front produced is "coarse". This is a *limitation* of the method, not a selling point — it is
written into the limitations section below.

---

## 4. Relation to the three baselines: where each one stands (consolidated)

We put the three pure-truck VRPTW baselines (OR-Tools, GA, PyVRP) next to BKS in one table
(`baseline_consolidated.csv`, 56 Solomon instances):

| Baseline | Mean gap vs BKS | Role |
|---|---:|---|
| **PyVRP** (standard open-source) | **−3.0%** | strongest baseline, community-standard solver |
| OR-Tools (commercial) | +7.2% | main comparison baseline |
| GA (own, 5-seed mean) | +36.7% ± 15.9% | own metaheuristic, honestly shown weak |

**Key honest point**: our V2 is a *collaborative heuristic* optimising a makespan-driven synchronous
objective; its "distance" is not directly comparable to these pure distance-minimising baselines.
Putting them side by side serves to show that "on standard truck VRPTW, a domain solver (PyVRP)
reaches or slightly beats BKS" — which in turn highlights that this project's real increment is in
*collaborative modelling*, not single-objective distance optimisation. This must be stated clearly,
otherwise it is easily misread as "my method is worse than PyVRP".

---

## 5. What the failure cases taught us (failure analysis is also depth)

Among the 17 failure cases, the most telling is this: on N=50 dense instances, the
**synchronous-feasibility rejection count reaches ~4.5 million**. This shows that the synchronous
rendezvous constraint (the drone must rejoin the truck path at some point) is the main bottleneck at
large scale — exactly corroborating the "benefit dilutes with scale" finding from §2, and jointly
bounding the method's applicability. Failure is not embarrassing; it *corroborates* the sensitivity
conclusion and together with it delimits where the method works.

---

## 6. Honest limitations (depth lands on self-awareness)

- **Greedy without local search**: applying intra-route 2-opt post-processing to V2 yields only
  0–1.76% — meaning once far-flung customers are offloaded, the truck route is already near-linear,
  so local search is nearly useless; it also shows the gain comes from *collaborative structure*,
  not route fine-tuning.
- **2–3 customers per sortie cap**: a simplification and a boundary; larger-scale multi-customer
  service needs heavier search.
- **Synthetic instances extended to 100, but the effective window lies at N ≤ 50**: we did not adopt
  the field's standard large-scale benchmark sets (e.g., the Solomon-derived FSTSP instances of
  Murray & Chu 2015 — which this project reproduced within their parameter range in W7; or the
  Masmoudi et al. 2018 set). At N=100 the synergy collapses to 2.3% and V2 averages 71.4/100 late
  customers (TW feasibility breaks down); extrapolation needs caution.
- **No MILP lower bound replicated**: the baseline comparison uses BKS (literature optimum) rather
  than a self-proven bound; absolute quality is anchored to the literature, not self-certified.

---

## 7. Summary: where this project's "depth" lies

Not in a fancier method (the greedy framework was never swapped) — but in building one **defensible
conclusion chain**:

> Controlled ablation locates the main gain source (multi-customer ability) → sensitivity confirms
> it from an independent angle (K sweep) → four parameters characterise the applicability window
> (dispersed customers / ample range / moderate scale) → scale extension to 100 reveals synergy
> collapse and TW breakdown (effective window N ≤ 50) → multi-objective proves dominance on both
> axes → three baselines honestly place V2's collaborative increment → failure cases corroborate
> the rendezvous constraint → limitations stated plainly (no LS / scale boundary / synthetic instances).

This chain lets every conclusion be traced back to an experiment, rather than resting on "I think
so". That is what depth means, and it is the spine the final report should follow.

---

*Data provenance:*
- `src/results/week07_ablation_*.csv` (5-config ablation)
- `src/results/week06_sensitivity.csv` + `figures/sensitivity_panels.png` (sensitivity, 5-seed mean±std)
- `src/results/week06_multi_objective.csv` + `figures/mo_*.png` (multi-objective trade-off)
- `src/results/baseline_consolidated.csv` + `figures/baseline_consolidated.png` (three baselines)
- `src/results/week06_largeN_*.csv` (N=30/50/100 decay) + `figures/largen_scale_decay.png`
- `docs/failure_cases_master.md` (17 failure cases)
- `src/results/schneider_evrptw_bks_comparison.csv` + `figures/schneider_routes.png` /
  `figures/schneider_vehcomp.png` (Schneider 2014 E-VRPTW replication, our routes vs BKS)
