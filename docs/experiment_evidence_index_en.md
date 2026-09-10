# Experiment Evidence Index

> Purpose: a single page collecting every **citable number** in this project, with data provenance and honest limitations, so the final report can lift figures directly without misattribution.
> All data here come from this project's own scripts and CSVs (under `src/results/`); no peer's report structure or framework is used.
> Companion doc: `docs/week06_depth_analysis_zh.md` (which turns these numbers into a defensible "why it works / when it works" chain).

---

## 1. Three baselines (pure-truck VRPTW, 56 Solomon instances vs BKS)

Source: `src/results/baseline_consolidated.csv` / `_summary.csv` (from `baseline_consolidated.py`).

| Baseline | Mean gap vs BKS | Role |
|---|---:|---|
| **PyVRP** (standard open-source solver) | **−3.0%** | strongest baseline, community standard |
| OR-Tools (commercial solver) | +7.2% | main comparison baseline |
| GA (own, 5-seed mean) | +36.7% ± 15.9% | own metaheuristic, honestly shown weak |

By family (gap vs BKS, PyVRP / OR-Tools / GA):

| Family | n | PyVRP | OR-Tools | GA (±std) |
|---|---:|---:|---:|---:|
| C1 | 9 | −2.3% | +4.2% | +25.9% ± 24.2% |
| C2 | 8 | −4.3% | +0.9% | +36.0% ± 16.3% |
| R1 | 12 | −3.2% | +5.1% | +31.2% ± 8.3% |
| R2 | 11 | −3.5% | +12.4% | +41.9% ± 6.3% |
| RC1 | 8 | −2.2% | +6.4% | +30.4% ± 2.0% |
| RC2 | 8 | −2.1% | +13.7% | +56.8% ± 5.1% |

**Honest point**: V2 is a collaborative heuristic optimising a makespan-driven synchronous objective; its "distance" is not directly comparable to these pure distance-minimising baselines. They are shown together to demonstrate that on standard truck VRPTW a domain solver (PyVRP) reaches or slightly beats BKS — highlighting that this project's contribution is in *collaborative modelling*, not single-objective distance optimisation.

---

## 2. Parameter sensitivity (5-seed mean ± std, n=12 except the scale sweep)

Source: `src/results/week06_sensitivity.csv` + `figures/sensitivity_panels.png` (from `week06_sensitivity.py`; rerun on 2026-09-10 after fixing a bug where the drone-range R parameter was not applied).

benefit = (V1 truck distance − V2 collaborative distance) / V1 distance × 100%.

| Param | Sweep | Synergy benefit (mean ± std) | Reading |
|---|---|---|---|
| Battery Q | 120→500 | 55.8%→47.1% (±~9.7) | larger battery → truck more self-sufficient → drone value diluted |
| **Range R** | 60→200 | **15.5%→27.7%→35.2%→50.5%@160→48.7%@200** | range <160 is a real bottleneck; saturates after 160 |
| Customers/sortie K | 1→3 | 25.3%→50.5%→56.5% (±8.6~16.5) | multi-customer ability is the main gain, consistent with ablation |
| Scale N | 8→30 | 63.8%→35.3% (±6.7~12.5) | larger scale dilutes the synergy benefit |

> Note: before 2026-09-10 the R sweep was flat at 50.5% because `mk_range` did not pass the range to the model; after the fix it varies as above, matching the narrative in depth-analysis §2.

---

## 3. Multi-objective trade-off (distance vs makespan, weighted-sum sweep)

Source: `src/results/week06_multi_objective.csv` + `figures/mo_*.png` (from `week06_multi_objective.py`).

| Variant | Mean distance | Mean makespan |
|---|---:|---:|
| V1 pure-truck EV | 486.4 | 622.4 |
| V2 collaborative (all w×seed mean) | 215.2 | 415.7 |

- Distance **−56%**, makespan **−33%**; V2 dominates V1 on **both axes** (holds per seed).
- Weights w ∈ {0, 0.25, 0.5, 0.75, 1.0}, 5 seeds; larger w favours distance at the cost of longer makespan.
- **Honest limitation**: weighted-sum scalarised greedy, not a full NSGA-II / Pareto solver — the front is "coarse". This is a method limitation, not a selling point.

---

## 4. Controlled ablation (5 configs, 40 instances, size 8/12/16/20)

Source: `src/results/week07_ablation_summary.csv` (from `week07_improvement_ablation.py`).

V2 makespan improvement vs Truck-only: size 8 → 39.2%, 12 → 37.8%, 16 → 32.4%, 20 → 29.9%.

Gain decomposition (pp contribution per size):

| Gain source | Range | Conclusion |
|---|---|---|
| **Multi-customer ability** (max_cust 1→2–3) | **+6.6 ~ 17.7 pp** | **main gain source** |
| Multi-takeoff | +4.1 ~ 7.3 pp | secondary |
| cap3 (3 customers/sortie) | +2.3 ~ 8.7 pp | upper extension of multi-customer ability |

sanity check: abl_cap1 (1 customer/sortie) ≡ published (M&C 2015) heuristic, confirming framework consistency.

---

## 5. Scale decay (N=30 / 50, 5 seeds)

Source: `src/results/week06_largeN_summary.csv` (from `week06_largeN.py`).

| Scale | V2 vs V1 benefit | Offload rate | Sync rejections | Mean TW violations |
|---|---:|---:|---:|---:|
| N=30 | 27.6% | 62.0% | 0.337 M | 8.0 / 30 |
| N=50 | 12.1% | 42.8% | 4.535 M | 24.0 / 50 |
| N=100 | 2.3% | 23.4% | 179.5 M | 71.4 / 100 |

At N=50 the V1 (battery+recharge) cost ≈ 5670 vs V0 (no battery) ≈ 3094 — the battery constraint alone nearly doubles the truck cost for N≥30, and the drone can only bypass a limited amount of recharge routing, so the synergy benefit is diluted. At **N=100** the synergy collapses to 2.3%, offload rate drops to 23.4%, and V2 averages **71.4/100 late customers** — the greedy cannot meet time windows at this scale (it was never TW-feasible by construction; `feasible` here means energy-only). The scale boundary is shown in `figures/largen_scale_decay.png`; the honest reading is that the *effective* collaboration interval lies at **N ≤ 50**.

---

## 6. Failure cases (17 entries, 1 strictly infeasible)

Source: `docs/failure_cases_master.md`. The most telling: on N=50 dense instances the **sync-feasibility rejection reaches ~4.5 million**, showing the synchronous rendezvous constraint is the main bottleneck at large scale — corroborating the "benefit dilutes with scale" finding in §2/§5 and jointly bounding the method's applicability.

---

## 7. Honest limitations (keep in the report)

Grouped by nature; each item gives its "consequence + next step" so it reads as a research-boundary statement, not a weakness list.

**Modeling-scope boundaries**
- **2–3 customers/sortie cap**: a deliberate simplification and a boundary. Multi-customer drone service is O(n⁴) enumeration, infeasible at scale; supporting more customers needs lighter search (e.g., pre-cluster then assign). Larger multi-customer collaboration is future work.
- **V2 does not yet re-introduce V1's battery/charging layer**: the truck-drone model (V2) is built on VRPTW and does not re-add the electric-vehicle battery and charging constraints of V1; a truly "electric truck + drone + charging station" joint optimization is a clear next step.

**Algorithmic-scope boundary**
- **Greedy without local search**: applying intra-route 2-opt to V2's constructed truck route (accept only strict makespan improvement) yields only 0–1.76% (peak 1.76% at N=16; see `week07_fstsp_with_ls.log`). By contrast, 2-opt on a plain OR-Tools route reaches −9.7% on CVRP n40 — showing V2's gain comes from the *collaborative structure* of offloading far-flung customers, not route fine-tuning; it also means V2 is already near the local optimum of its current neighborhood. **How far from global optimum remains unquantified** (unless a MILP bound or larger neighborhoods like 3-opt are added), left for future work.

**Empirical-validation boundaries**
- **Synthetic instances extended to 100, but the effective collaboration interval lies at N ≤ 50**: our truck-drone experiments use randomly generated synthetic instances and do not adopt the field's standard large-scale benchmark sets (e.g., the Solomon-derived FSTSP instances of Murray & Chu 2015 — which this project reproduced within their parameter range in W7; or the Masmoudi et al. 2018 instance set). At N=100 the synergy collapses to 2.3% and V2 averages 71.4/100 late customers (TW feasibility breaks down); extrapolation to real large scale needs caution.
- **No MILP lower bound replicated**: baselines are anchored to BKS (literature optimum), not a self-proven bound. Computing exact bounds for this NP-hard problem is itself a separate research contribution, beyond this project's scope; absolute quality is therefore literature-anchored, not self-certified.
- **Coarse MO front**: the weighted-sum greedy gives a "partial / inner" front and may miss non-convex Pareto regions; it is not a full Pareto solver (see §3). For a complete front, the natural next step is ε-constraint or NSGA-II (as in peer Xie's P-ACO/NSGA-II).

---

## 8. Data provenance (reproducible)

| Result | Script | CSV | Figure |
|---|---|---|---|
| Three baselines | `baseline_consolidated.py` | `baseline_consolidated.csv` / `_summary.csv` | `baseline_consolidated.png` / `pyvrp_family_gap.png` |
| PyVRP baseline | `baseline_pyvrp_vrptw.py` | `baseline_pyvrp_vrptw_results.csv` | `pyvrp_family_gap.png` |
| GA baseline | `baseline_ga_vrptw.py` | `baseline_ga_vrptw_results.csv` | — |
| Sensitivity | `week06_sensitivity.py` | `week06_sensitivity.csv` | `sensitivity_panels.png` |
| Multi-objective | `week06_multi_objective.py` | `week06_multi_objective.csv` | `mo_scatter.png` / `mo_tradeoff.png` |
| Ablation | `week07_improvement_ablation.py` | `week07_ablation_raw.csv` / `_summary.csv` | — |
| Scale | `week06_largeN.py` | `week06_largeN_results.csv` / `_summary.csv` | `largen_scale_decay.png` |
| FSTSP reproduction | `week07_fstsp_repro.py` | `week07_fstsp_raw.csv` / `_summary.csv` | — |

Seed convention: all multi-seed experiments use fixed seed sets (e.g., `20260910–20260914`, or GA's `20260717/20260801/20260815/20260901/20261001`) for reproducibility; CSVs are excluded from the repo by design and regenerated locally via scripts + seeds.
