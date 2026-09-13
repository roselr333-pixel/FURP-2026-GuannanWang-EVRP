# Experiment Evidence Index

> Purpose: a single page collecting every **citable number** in this project, with data provenance and limitations, so figures can be lifted directly without misattribution.
> All data here come from this project's own scripts and CSVs (under `src/results/`); no peer's report structure or framework is used.
> Companion docs: `docs/analysis/week06_depth_analysis_zh.md` and `docs/analysis/week06_depth_analysis_en.md` (which turn these numbers into a coherent "why it works / when it works" chain; the two are independent files, not sentence-by-sentence translations).

---

## 1. Three baselines (pure-truck VRPTW, 56 Solomon instances vs BKS)

Source: `src/results/baseline_consolidated.csv` / `_summary.csv` (from `baseline_consolidated.py`).

| Baseline | Mean gap vs BKS | Role |
|---|---:|---|
| **PyVRP** (standard open-source solver) | **−3.0%** | strongest baseline, community standard |
| OR-Tools (commercial solver) | +7.2% | main comparison baseline |
| GA (own, 5-seed mean) | +36.6% ± 15.8% | own metaheuristic, weaker than the other two |

By family (gap vs BKS, PyVRP / OR-Tools / GA):

| Family | n | PyVRP | OR-Tools | GA (±std) |
|---|---:|---:|---:|---:|
| C1 | 9 | −2.3% | +4.2% | +25.9% ± 24.2% |
| C2 | 8 | −4.3% | +0.9% | +36.0% ± 16.3% |
| R1 | 12 | −3.2% | +5.1% | +31.2% ± 8.2% |
| R2 | 11 | −3.5% | +12.4% | +41.5% ± 6.0% |
| RC1 | 8 | −2.2% | +6.4% | +30.6% ± 2.4% |
| RC2 | 8 | −2.1% | +13.7% | +56.8% ± 5.1% |

V2 is a collaborative heuristic optimising a makespan-driven synchronous objective; its "distance" is not directly comparable to these pure distance-minimising baselines. They are shown together to demonstrate that on standard truck VRPTW a domain solver (PyVRP) reaches or slightly beats BKS. OR-Tools uses GUIDED_LOCAL_SEARCH with a 10 s cap and is stochastic; re-runs vary by ≈ ±0.1 pp (the figures above come from the consolidated CSV, which is the cited source).

---

## 2. Parameter sensitivity (5-seed mean ± std, n=12 except the scale sweep)

Source: `src/results/week06_sensitivity.csv` + `figures/sensitivity_panels.png` (from `week06_sensitivity.py`).

benefit = (V1 truck distance − V2 collaborative distance) / V1 distance × 100%.

| Param | Sweep | Synergy benefit (mean ± std) | Reading |
|---|---|---|---|
| Battery Q | 120→500 | 41.2%→29.7% (±~8.8~11.6) | larger battery → truck more self-sufficient → drone value diluted |
| **Range R** | 60→200 | **15.4%→24.6%→32.4%→34.4%@160→34.4%@200** | range <160 is a real bottleneck; saturates after 160 |
| Customers/sortie K | 1→3 | 20.5%→34.4%→37.1% (±4.5~13.1) | multi-customer ability is the main gain, consistent with ablation |
| Scale N | 8→30 | 35.3%→32.1% (±3.0~12.2) | larger scale dilutes the synergy benefit |

> Note: before 2026-09-10 the R sweep was flat at 50.5% because `mk_range` did not pass the range to the model.

---

## 3. Multi-objective trade-off (distance vs makespan, weighted-sum sweep)

Source: `src/results/week06_multi_objective.csv` + `figures/mo_*.png` (from `week06_multi_objective.py`).

| Variant | Mean distance | Mean makespan |
|---|---:|---:|
| V1 pure-truck EV | 486.5 | 622.5 |
| V2 collaborative (all w×seed mean) | 330.7 | 413.6 |

- Distance **−32%**, makespan **−34%**; V2 dominates V1 on **both axes** (holds per seed).
- Weights w ∈ {0, 0.25, 0.5, 0.75, 1.0}, 5 seeds; larger w favours distance at the cost of longer makespan.
- **Limitation**: weighted-sum scalarised greedy, not a full NSGA-II / Pareto solver — the front is "coarse". This is a method limitation.

---

## 4. Controlled ablation (5 configs, 40 instances, size 8/12/16/20)

Source: `src/results/week07_ablation_summary.csv` (from `week07_improvement_ablation.py`).

V2 makespan improvement vs Truck-only: size 8 → 34.5%, 12 → 29.0%, 16 → 28.7%, 20 → 24.8%.

Gain decomposition (pp contribution per size):

| Gain source | Range | Conclusion |
|---|---|---|
| **Multi-customer ability** (max_cust 1→2–3) | **+8.6 ~ 12.1 pp** | **main gain source** |
| Multi-takeoff | +2.2 ~ 4.4 pp | secondary |
| cap3 (3 customers/sortie) | +0.6 ~ 8.9 pp | upper extension of multi-customer ability |

sanity check: abl_cap1 (1 customer/sortie) ≡ published (M&C 2015) heuristic, confirming framework consistency.

**Re-run on standard instances**: the same heuristic and evaluator on official Solomon topologies (C101/C201/R101/RC101 x 3 customer windows x N=8/12/16/20 = 48 instances) decompose into a multi-customer gain of **+7.2 ~ 8.9 pp**, a multi-takeoff gain of **+1.3 ~ 2.0 pp** and cap3 of +3.9 ~ 7.7 pp; `abl_cap1` still equals published instance by instance. The main gain source matches the synthetic run, but its size depends on the spatial pattern (14.1pp on uniform R101 against 5.7pp on clustered C101). Source: `src/results/week07_ablation_std_summary.csv` (`week07_ablation_std.py`), figure `figures/ablation_std.png`, note `docs/weekly/week07_ablation_std_note_en.md`.

**The same decomposition on the V3 model (electric + time windows)**: moved onto the model where the truck has a battery, may detour to recharge and customers have time windows (40 instances x 4 configs), multi-customer ability is still the largest single gain — **+12.5 / +8.5 / +10.9 pp** at N=8/12/16 (pooled Wilcoxon p=5.3×10⁻³) — and turns to **−2.8 pp** at N=20. Reusing one truck stop for several sorties is only a secondary factor (**+1.9 to +5.3 pp**, p=2.4×10⁻⁴, non-zero on just 20 of 40 pairs), and cap3 is not significant (p=0.139). All four configurations are 100% energy-feasible. The attribution matches the FSTSP setting — multi-customer ability is the main gain source — except that under V3 it runs out by N=20. Source: `src/results/v3_ablation_summary.csv` (`v3_ablation.py`), figure `figures/v3_ablation.png`, note `docs/weekly/v3_ablation_note_en.md`.

**The same ablation under a drone energy / payload model**: adding a payload capacity `P_MAX` and an energy budget `E_D` that grows with the load on board (with `BETA=0` this reduces exactly to the old range limit, verified value-for-value on 300 random plans) erodes the multi-customer gain without changing its direction — from **+10.4pp down to +6.1pp** on the synthetic set (BETA 0 to 0.04) and from +6.6pp to +5.4pp on the standard set — while cap3 stops paying (−0.5 to +0.4pp). Feasibility is the other result: the energy-unaware published heuristic is only 42% (synthetic) / 48% (standard) energy-feasible at BETA=0.04, while my greedy is 100% feasible at every BETA. Source: `src/results/drone_energy_summary.csv` (`drone_energy_ablation.py`), figure `figures/drone_energy.png`, note `docs/weekly/drone_energy_note_en.md`.

---

## 5. Scale decay (N=30 / 50 / 100, 5 seeds)

Source: `src/results/week06_largeN_summary.csv` (from `week06_largeN.py`).

| Scale | V2 vs V1 benefit | Offload rate | Sync rejections | Mean TW violations |
|---|---:|---:|---:|---:|
| N=30 | 8.6% | 11.3% | 0.122 M | 20.4 / 30 |
| N=50 | 3.4% | 5.2% | 1.012 M | 39.0 / 50 |
| N=100 | 0.5% | 2.8% | 22.531 M | 88.6 / 100 |

At N=50 the V1 (battery+recharge) cost ≈ 5670 vs V0 (no battery) ≈ 3094 — the battery constraint alone nearly doubles the truck cost for N≥30, and the drone can only bypass a limited amount of recharge routing, so the synergy benefit is diluted. At **N=100** the synergy collapses to 0.5%, offload rate drops to 2.8%, and V2 averages **88.6/100 late customers** — the greedy cannot meet time windows at this scale (it was never TW-feasible by construction; `feasible` here means energy-only). The scale boundary is shown in `figures/largen_scale_decay.png`; the reading is that the *effective* collaboration interval narrows to **N ≤ 30** (only 3.4% is left at N=50). One of the five N=100 instances is also capacity-infeasible (demand 1081 > CAP=1000, see §5b), so that row averages the other four.

## 5b. Truck capacity (CAP=1000, now enforced)

Source: `src/results/week06_capacity_summary.csv` (`week06_capacity_study.py`), figure `figures/capacity_binding.png`.

`CAP` used to be declared but unchecked, so every ground-air number above was computed on a capacity-free model. It is now enforced — the demand carried on the truck route may not exceed the cap, and offloading a customer to the drone removes its demand from the truck — and the collaborative greedy repairs an overload (cheapest feasible offload first) before it maximises the makespan gain.

| Cap | Sizes where it binds | V2 repairs the overload | Demand range |
|---|---|---:|---:|
| **1000 (declared)** | N=100, 1 of 5 instances (demand 1081) | 0% of the binding cells | 81 … 994 units for N=8 … N=100 |
| 600 | N=100, 5/5 | 0% | same |
| 400 | N=50, 5/5; N=100, 5/5 | 0% | same |

Three readings:

- **The declared cap is free where the published results live.** Total demand is at most 533 units on the N≤50 seeds, so the W6 headline (N=8–20) re-runs byte-identical and the N=30/50 rows above are unchanged; only the N=100 instance with demand 1081 exceeds 1000, and it is capacity-infeasible for V0, V1 and V2 (V2 repairs 1081 → 1026, still above the cap). That instance is therefore excluded from the N=100 row, which averages the other four.
- **When the cap binds, the drone cannot rescue the plan.** V2 leaves 64.7% (N=8) to 97.2% (N=100) of the demand on the truck, i.e. one serial drone removes only 35.3% → 2.8% of it, so every binding cell in the study stays infeasible. In practice the constraint behaves like a hard "total demand ≤ cap" bound; the natural fixes are a load-aware LNS or several drones.
- **Capacity and energy are separate gates.** At N=100 V1/V2 are energy-feasible in 0 of 5 instances (the truck route fails the battery/recharge model), so the N=100 feasibility collapse must not be attributed to capacity alone.

## 5c. Do the synthetic conclusions transfer? (Schneider 2014 data)

Source: `src/results/week06_std_evrp_summary.csv` (`week06_standard_instances.py`), figure `figures/std_instances.png`.

Every W6 number above comes from random geometry. `std_evrp_instances.make_evrp` converts the original **Schneider (2014) E-VRPTW instances** — real coordinates, real time windows, the real charging stations and the paper's own vehicle parameters — into the W6 instance format (time unit = minutes because the paper sets `v = 1`; service 90 min; battery `Q/r` = 79.7 distance units; full recharge `Q·g` = 270 min; capacity `C` = 200; drone range = 2.5 × the instance's mean depot-customer distance). The same evaluators and variants are then re-run: 6 families × 4 customer subsets = **24 samples per size**.

| N | standard gain | synthetic reference | late customers V1 → V2 | V2 offload | V2 recharges |
|---|---:|---:|---:|---:|---:|
| 8 | **54.8%** | 34.5% | 5.17 → 0.96 | 17.2% | 0.96 |
| 12 | **48.8%** | 29.0% | 8.79 → 2.92 | 13.9% | 1.42 |
| 16 | **43.7%** | 28.7% | 12.71 → 4.96 | 13.8% | 1.96 |
| 20 | **41.0%** | 24.8% | 16.96 → 7.71 | 11.7% | 2.17 |

- **The synthetic gain is conservative.** With the W6 capacity the same model is 1.5-1.7x better on standard data at every size, and the ordering (benefit shrinking with N) is unchanged.
- **The drone also repairs time windows**: late customers fall by 4.2 / 5.9 / 7.8 / 9.3 per instance. The synthetic instances show the same direction, but Schneider's much tighter windows make it a headline effect.
- **The paper's fleet capacity exposes the single-truck assumption**: with the paper's own `C = 200` the truck is capacity-infeasible on 0/24 samples at N=8, 7/24 at N=12 and 12/24 at N=16/20 (V2 feasibility 100 / 100 / 58 / 50%); with the W6 default `CAP = 1000` all 96 samples are feasible. This is the §5b boundary, re-measured on standard data.
- Caveat: these are one-truck runs on instances designed for a fleet (`m` = 7-30 vehicles), so they measure the relative value of the drone under real geometry, windows and battery — not a Schneider-equivalent solution cost (that comparison is in `docs/baselines/schneider_evrptw_replication_en.md`).



---

## 5d. Drone energy / payload gates on the main line (V3 and W8)

Source: `src/results/drone_energy_mainline_summary.csv` (from `drone_energy_mainline.py`), figure `figures/drone_energy_mainline.png`.

`drone_energy.py` gives the drone a payload capacity `P_MAX` and an energy budget `E_D` that grows with the load still on board, and the same four parameters (`alpha`/`beta`/`ed`/`p_max`) now sit on the V3 evaluator (`v3_ev_collab.ev_collab_k`) and on the W7/W8 FSTSP evaluator (`week07_fstsp_repro.fstsp_simulate[_multi]`), with `beta = 0`, `ed = R_D` and no payload cap as the default. Running both at `beta = 0.02` with `E_D = 160` and `P_MAX = 30` (4 sizes x 10 seeds x K = 1/2/3):

| Model | BETA = 0.00 (greedy / K=1 / K=2 / K=3) | BETA = 0.02 | Feasible at 0.02 |
|---|---:|---:|---:|
| V3 (EV + TW) | 643 / 513 / 413 / 361 | 664 / 521 / 444 / 390 | 100% |
| W8 (FSTSP) | 497 / 407 / 318 / 276 | 508 / 407 / 334 / 295 | 100% |

The gates cost a few percent of makespan and leave the gains in place (V3 K=1 goes 52.4% -> 53.0% at N=8 and 33.5% -> 34.5% at N=20; W8 K=3 goes 69.6% -> 70.6% and 54.0% -> 51.2%), but they eat into the marginal value of extra drones: K=1 -> K=3 goes from 42.1/42.2/27.2/22.3% to 41.3/42.4/18.6/17.1% at N=8/12/16/20 (W8: 46.6/40.8/32.6/21.2% to 49.4/39.1/23.0/15.9%), i.e. 5-10 pp less at N >= 16. Every returned plan is feasible under the gate, against 42-48% feasibility for the energy-unaware published heuristic in §4. Detail: `docs/weekly/drone_energy_note_en.md` §4b.

## 6. Failure cases (13 entries, 1 strictly infeasible)

Source: `docs/reference/failure_cases_master.md`. The most telling: on N=50 dense instances the **sync-feasibility rejection reaches ~4.5 million**, showing the synchronous rendezvous constraint is the main bottleneck at large scale — corroborating the "benefit dilutes with scale" finding in §2/§5 and jointly bounding the method's applicability.

---

## 7. Schneider (2014) E-VRPTW replication (constructive greedy + local search vs BKS)

Source: `src/results/schneider_evrptw_baseline.csv` (my solver, 92 instances) and
`src/results/schneider_evrptw_bks_comparison.csv` (18 instances with BKS: 5-customer C5 set from
jmanzolli/E-VRPTW citing Schneider 2014; 100-customer _21 set from Adachi et al. 2022 citing
Schneider 2014). My solver is a constructive greedy with a homogeneous multi-trip fleet
(MIN vehicles then MIN distance), feasibility-checked on capacity + time windows (waiting allowed)
+ full recharge at stations; the construction is then refined by `schneider_improve.py` (cheapest-station repair, trip move/merge, customer relocate/swap, 2-opt) under the same hierarchy. Figures: `figures/schneider_routes.png` (route maps for 4
representative instances with BKS distance & vehicle gap annotated per panel),
`figures/schneider_vehcomp.png` (vehicle count, mine vs BKS across 18 instances).

**Caveat**: BKS route geometry is not publicly available (only distance values from the
secondary literature), so the comparison is at the aggregate level (distance + vehicle count),
not a route-geometry overlay I cannot produce. My 92 instances were byte-verified against the
jmanzolli/E-VRPTW "E-VRPTW Instances" folder (whitespace-only diff), confirming they are the
Schneider ORIGINAL data. My solver is deterministic as of 2026-09-10 (the unassigned-customer set
is iterated in sorted ID order, removing Python's per-process hash randomisation), so every number
below reproduces exactly on re-run.

Aggregate (18 instances with BKS):
- Mean distance gap vs BKS: **+21.3%** (absolute mean) after the local search, down from **+52.7%**
  for the construction alone; three instances (c208C5, r105C5, rc208C5) match the BKS exactly.
- Mean vehicle count: mine **3.28** vs BKS **2.06** (was 5.44). The residual gap is concentrated on
  the 100-customer _21 set (mean +43.6%, max +97.2% on c201_21 with 6 vs 4 vehicles): fleet packing,
  not route geometry, is what is left.
- A modelling bug found while adding the search: the depot closing time was unchecked for the first
  trip of a new vehicle (3 of the 18 instances returned after the depot closed). It is now enforced
  for every trip, which moved the constructive baseline from +50.7% to +52.7%.
- A few C5 wins: c103C5 −0.4%, r105C5 −4.4% (my greedy is competitive on a couple of
  small/loose-time-window instances; the heavy losses are on 100-customer + tight-TW instances).

---

## 8. LNS improvement + significance tests (W8)

Source: `src/results/week08_lns_summary.csv` (from `week08_lns.py`); significance in `src/results/stat_tests.csv` (`stat_tests.py`, numpy-only, no new dependency); figure `figures/lns_vs_greedy.png`.

A destroy-and-repair LNS (random / worst / whole-sortie destroy + truck / single / paired repair + simulated-annealing acceptance) on top of the greedy V2, same FSTSP evaluator, 10 seeds × 6 sizes (N=8/12/16/20/30/50):

| Size | truck-only | V2 greedy | greedy+2-opt | greedy+LNS | LNS vs greedy |
|---|---:|---:|---:|---:|---:|
| N=8 | 391.3 | 256.0 | 247.7 | **222.2** | **+12.51%** |
| N=12 | 579.4 | 412.1 | 400.2 | **338.5** | **+16.78%** |
| N=16 | 774.8 | 554.4 | 533.9 | **471.0** | **+13.29%** |
| N=20 | 1022.3 | 767.2 | 746.3 | **594.4** | **+21.32%** |
| N=30 | 1597.7 | 1270.1 | 1220.6 | **1037.4** | **+16.91%** |
| N=50 | 3114.1 | 2641.3 | 2588.4 | **2188.4** | **+16.59%** |

- LNS improves the greedy by a consistent **+12.5% to +21.3% at every size**; paired Wilcoxon overall **p = 1.7×10⁻¹⁰**, significant at every size.
- LNS offsets the scaling decay: the greedy's reduction vs truck-only falls 34.5% → 15.2% (N=8→50), while LNS only falls 43.1% → 29.5%; at N=50 LNS still gives 29.5%.
- Intra-route 2-opt alone adds about 2%~3.2%, so the gain comes mainly from re-allocating drone tasks and the overall structure, not route fine-tuning.
- Deterministic: one seed-derived RNG per instance, fixed iteration budget; the same seed reproduces the same numbers.

Paired Wilcoxon signed-rank, overall rows (negative mean diff = first method smaller; n = nonzero pairs):

| Comparison | n | mean diff | p |
|---|---:|---:|---:|
| my V2 vs published M&C 2015 | 38 | −73.2 | 2.4×10⁻⁷ |
| my V2 vs abl_cap1 (multi-customer) | 38 | −73.2 | 2.4×10⁻⁷ |
| my V2 vs abl_notakeoff (multi-takeoff) | 23 | −37.7 | 2.9×10⁻⁵ |
| LNS vs greedy V2 | 54 | −194.3 | 1.7×10⁻¹⁰ |
| V2 vs V1 (collaborative vs EV) | 40 | −182.1 | 3.71×10⁻⁸ |

**Multiple drones (W8 extension, breaking the single-drone limitation)**: K parallel serial drones, same instances and seeds; K=1 is numerically identical to the single-drone evaluator. LNS reduction vs truck-only:

| size | K=1 | K=2 | K=3 |
|---|---:|---:|---:|
| N=8 | 43.1% | 60.1% | **69.6%** |
| N=20 | 41.6% | 51.2% | **54.0%** |
| N=50 | 29.5% | 35.4% | **38.1%** |

K=1→3 lifts the benefit at every size (N=50: 29.5%→38.1%) and raises the scaling-decay curve; the LNS still adds +7%~+23% at every K. Paired Wilcoxon: LNS K=3 vs K=1 and K=2 vs K=1 both **p=1.67×10⁻¹¹** overall, significant at every size. Source `week08_multidrone.py` → `week08_multidrone_summary.csv`; figure `figures/multidrone.png`; note `docs/weekly/week08_multidrone_note_en.md`.

**Standard instances + more drones + scheduling (W8 extension 2)**: official Solomon topologies (C101/C201/R101/RC101, first n customers, rescaled to the synthetic RMS radius), K=1/2/3/5, n=10/20/30/50 (16 standard instances). LNS benefit vs truck-only:

| size | K=1 | K=2 | K=3 | K=5 |
|---|---:|---:|---:|---:|
| N=10 | 37.2% | 51.2% | 61.1% | **71.4%** |
| N=50 | 27.5% | 38.4% | 42.7% | **46.8%** |

More drones give a higher benefit and flatten the scaling decay (uniform-random R101 benefits most, clustered C101 least). **Scheduling**: greedy vs local vs optimal (branch and bound, <= 14 sorties) plus a lower-bound certificate (the larger of: every sortie on its own drone, and total flight divided by K). After the main evaluator was made physical the sortie sets no longer overlap, so the K drones have **no contention**: **greedy == the lower bound on 64/64 configs (provably optimal)**, local gain **0.000%**, and against the exact optimum (32 configs) the naive rule is **0.000% above it**. The earlier "31/64 + a small local gain" was a false contention created by nested sorties.

**Original Murray & Chu (2015) FSTSP instances** (note `docs/weekly/week08_mc_benchmark_note_en.md`): the original set was downloaded from the hosting by Dell'Amico's group into `src/instances/murray_chu_2015/` (36 ten-customer instances, 11 shipping a literature OFV). The bundled README never says which of `tau`/`tauprime` is the truck; calibrating on **36/36 instances** shows `tauprime`'s implied speed matches the declared UAV speed (0.2/0.4/0.6), so `tau` = truck and `tauprime` = UAV.

| config | vs truck-only TSP | LNS / literature OFV |
|---|---:|---:|
| c1K1 (exactly M&C's FSTSP: one customer per sortie, one drone) | 22.3% | **0.924** |
| c1K3 | 37.2% | 0.692 |
| c2K3 (my multi-customer extension) | 38.2% | 0.678 |

So **under M&C's own FSTSP definition my LNS beats the objective shipped with the instances by about 7.6%**. The files carry no drone endurance, so endurance is unlimited and the longest flight per solution is reported (mean 25-29, max about 69).

**V3: electric truck + drone + charging + time windows** (note `docs/weekly/v3_ev_collab_note_en.md`): the week06 battery, charging stations and time windows are stacked back into the collaborative model and extended to multiple drones (K=1/2/3). The route lists customers only and charging detours are inserted by the evaluator, so the LNS destroy/repair is reused as is. 10 seeds per size:

| size | V1 truck EV | V3 + LNS K=1 | V3 + LNS K=2 | V3 + LNS K=3 |
|---|---:|---:|---:|---:|
| N=8 | 485.8 | 230.6 (**52.4%**) | 170.8 (64.6%) | 133.4 (**72.5%**) |
| N=20 | 1283.6 | 850.5 (33.5%) | 707.1 (44.5%) | 661.0 (48.3%) |

TW violations and recharges (V1 -> V3l): N=8 is 2.4/0.9 -> 0/0; N=20 is 13.5/2.9 -> 6.9/1.7 (K=1).

**The electric and time-window constraints amplify the drone's value**: K=1 reaches **33.5%~52.4%**, still above the 23%~45% the same methods reach in the FSTSP setting, and K=2/3 push to **44.5%~72.5%**, because offloading shortens the truck route and removes most charging detours and late arrivals. **Evaluator corrections**: this evaluator has been corrected twice, both times for treating one drone as if it could fly several sorties at once — (1) the original single-drone evaluator did not track the drone's own availability (the earlier 56.7%~87.8% came from this), and now assigns sorties sequentially through `avail[d]`; (2) sequential assignment still lacked the check that the drone assigned to a sortie is back on the truck at the launch node, so the code merely delayed the launch although the truck had already left that node — such plans are now infeasible (`schedule_inf`, infinite makespan). After both corrections the single-drone reduction is 33.5%~52.4%. The core FSTSP line (week06/08) uses the separate `fstsp_simulate` / `drone_scheduling`, never affected. Source `v3_ev_collab.py` -> `v3_ev_collab_summary.csv`.

**Exact optimality gap (CP-SAT, small instances)** (note `docs/weekly/week08_exact_gap_note_en.md`): CP-SAT computes the exact optimum of the physical FSTSP model (`cpsat_fstsp.solve_exact`; two independent checks: zero range reduces to a truck TSP matching Held-Karp, and n=5 matches an exhaustive enumeration). gap = (heuristic − optimum)/optimum:

| size | proven optimal | greedy gap | LNS gap | original V2 plan valid |
|---|---:|---:|---:|---:|
| n=8 | **5/5** | **31.2%** | **16.5%** | 5/5 |
| n=10 | 0/5 | 58.0% | 26.4% | 5/5 |
| n=12 | 0/5 | 49.1% | 23.5% | 5/5 |

**The LNS roughly halves the gap**, quantifying the improvement phase. At n≥10 optimality is not proved (the value is an upper bound, so the gap is a lower bound). The shared FSTSP evaluator has a physical defect: it does not check that the drone is back on the truck, so nested/crossing sorties are given a makespan although such a plan is infeasible — measured on 15 instances, the original V2 produces such an invalid plan in 14 of them (the FC-7-2/7-3 defect, on the FSTSP evaluator path). Source `week08_exact_gap.py` + `cpsat_fstsp.py` -> `week08_exact_gap_raw.csv` / `_summary.csv`. With the main evaluator physical and everything re-run, the V2 plans are now valid on 15/15 instances.

---

## 9. Limitations

Grouped by nature; each item gives its "consequence + next step" so it reads as a research-boundary statement, not a weakness list.

**Modeling-scope boundaries**
- **2–3 customers/sortie cap**: a deliberate simplification and a boundary. Multi-customer drone service is O(n⁴) enumeration, infeasible at scale; supporting more customers needs lighter search (e.g., pre-cluster then assign). I have left larger multi-customer collaboration to later work.
- **The battery/charging layer is now re-introduced by V3**: V3 (electric truck + drone + charging stations + time windows) is implemented and compared against V1 (see §8); what is still missing is wiring **multiple drones** into V3.

**Algorithmic-scope boundary**
- **The greedy itself has no local search (W8 adds an improvement phase)**: applying intra-route 2-opt to V2's constructed truck route (accept only strict makespan improvement) yields only 2.5–3.1% (peak 3.08% at N=16; see `week07_fstsp_log.txt`) — showing V2's gain comes from the *collaborative structure* of offloading far-flung customers, not route fine-tuning. With the W8 destroy-and-repair LNS the gain over the greedy is a consistent +9% to +12.6% at every size (Wilcoxon overall p=1.7×10⁻¹⁰; see §8), beyond pure routing. **How far from global optimum is now quantified in §8** (CP-SAT exact optimum; n=8 proven: greedy +31.2%, LNS +16.5%).

**Empirical-validation boundaries**
- **Synthetic instances extended to 100, but the effective collaboration interval narrows to N ≤ 30**: my truck-drone experiments use randomly generated synthetic instances and do not adopt the field's standard large-scale benchmark sets (e.g., the Solomon-derived FSTSP instances of Murray & Chu 2015 — which this project reproduced within their parameter range in W7; or the Masmoudi et al. 2018 instance set). At N=100 the synergy collapses to 0.5% and V2 averages 88.8/100 late customers (TW feasibility breaks down); extrapolation to real large scale needs caution. The W8 LNS lifts the N=50 collaboration benefit from the greedy's 15.2% to 29.5%, slowing the decay, but it is still the same synthetic instances and setting, so the boundary is unchanged. **W8 extension 2 re-ran 16 standard instances built from official Solomon topologies (K=1/2/3/5) with the same conclusion**; **the original Murray & Chu (2015) instances were also downloaded** (36 ten-customer instances, see §8), so the results no longer rest on synthetic or rescaled Solomon data alone. What is still missing is standard-benchmark validation at larger sizes (N > 50).
- **Drone scheduling: provably optimal on every config after the physical fix**: with the lower bound (the larger of every sortie on its own drone, and total flight divided by K) as a certificate, greedy reaches that bound on **64/64 configs** and local search adds **0.000%** once the sortie sets no longer overlap (physical evaluator). The earlier "31/64 + a small local gain" was a false contention created by nested sorties. (Limitation: this holds for physically valid, non-overlapping sortie sets; if sorties did overlap, contention would return.)
- **Both shared evaluators are now physical, and W6/W7/W8 were re-run**: `week07_fstsp_repro.fstsp_simulate` and `week06_ground_air_evrp_tw.simulate` both reject nested/crossing sorties, both require the drone to be recovered before the next sortie, and both make the truck wait at the recovery node (returning inf for an infeasible plan). W7/W8, the W6 headline, `week06_largeN` and the V2-vs-V1 row of `stat_tests` were re-run (see `docs/analysis/evaluator_physical_fix_note_en.md`). The numbers are lower but the direction is unchanged: the W6 headline V2-vs-V1 advantage falls from 42-55% to **16-34%**, and the scaling decay from 27.6/12.1/2.3% to **8.6/3.4/0.5%**. V0/V1 involve no drone and are unchanged.
- **Time windows / energy are now covered by V3, which is also extended to multiple drones**: V3 stacks the week06 battery, charging stations and time windows back into the truck-drone model (see §8), reaching 34.7%~53.4% over the truck-only EV baseline at K=1 and 57.7%~72.8% at K=2/3, removing most late arrivals and charging detours. V3 is now tested with K=1/2/3, and time windows are still a penalty in the search rather than a hard constraint (the violation count is reported).
- **The exact optimum is now computed at small scale (§8); at larger scale it is still unprovable**: CP-SAT solves the physical FSTSP model exactly — n=8 is proven optimal (greedy +31.2%, LNS +16.5%), while n=10/12 give an upper bound on the optimum within 180s (so those gaps are lower bounds). Exact optima / bounds at larger scale remain open and are the natural next improvement. Baseline absolute quality is still anchored to BKS (literature optimum).
- **Coarse MO front**: the weighted-sum greedy gives a "partial / inner" front and may miss non-convex Pareto regions; it is not a full Pareto solver (see §3). For a complete front, the natural next step is ε-constraint or NSGA-II (as in peer Xie's P-ACO/NSGA-II).

---

## 10. Data provenance (reproducible)

| Result | Script | CSV | Figure |
|---|---|---|---|
| Three baselines | `baseline_consolidated.py` | `baseline_consolidated.csv` / `_summary.csv` | `baseline_consolidated.png` / `pyvrp_family_gap.png` |
| PyVRP baseline | `baseline_pyvrp_vrptw.py` | `baseline_pyvrp_vrptw_results.csv` | `pyvrp_family_gap.png` |
| GA baseline | `baseline_ga_vrptw.py` | `baseline_ga_vrptw_results.csv` | — |
| Sensitivity | `week06_sensitivity.py` | `week06_sensitivity.csv` | `sensitivity_panels.png` |
| Multi-objective | `week06_multi_objective.py` | `week06_multi_objective.csv` | `mo_scatter.png` / `mo_tradeoff.png` |
| Ablation | `week07_improvement_ablation.py` | `week07_ablation_raw.csv` / `_summary.csv` | — |
| Scale | `week06_largeN.py` | `week06_largeN_results.csv` / `_summary.csv` | `largen_scale_decay.png` |
| Capacity | `week06_capacity_study.py` | `week06_capacity_raw.csv` / `_summary.csv` | `capacity_binding.png` |
| Standard instances | `week06_standard_instances.py` + `std_evrp_instances.py` | `week06_std_evrp_raw.csv` / `_summary.csv` | `std_instances.png` |
| LNS improvement | `week08_lns.py` | `week08_lns_raw.csv` / `_summary.csv` | `lns_vs_greedy.png` |
| Multi-drone | `week08_multidrone.py` (+ week07 K-drone evaluator) | `week08_multidrone_raw.csv` / `_summary.csv` | `multidrone.png` |
| Multi-drone (standard) | `week08_multidrone_std.py` + `fstsp_instances.py` | `week08_multidrone_std_raw.csv` / `_summary.csv` | `multidrone_std.png` |
| Drone scheduling | `drone_scheduling.py` | `week08_scheduling.csv` | — |
| Original M&C benchmark | `week08_mc_benchmark.py` + `fstsp_mc.py` | `week08_mc_benchmark_raw.csv` | — |
| V3 (electric + drone + TW) | `v3_ev_collab.py` | `v3_ev_collab_raw.csv` / `_summary.csv` | — |
| Drone energy / payload ablation | `drone_energy_ablation.py` + `drone_energy.py` | `drone_energy_raw.csv` / `_summary.csv` | `drone_energy.png` |
| Drone energy on the main line | `drone_energy_mainline.py` + `drone_energy.py` | `drone_energy_mainline_raw.csv` / `_summary.csv` | `drone_energy_mainline.png` |
| Exact optimality gap (CP-SAT) | `week08_exact_gap.py` + `cpsat_fstsp.py` | `week08_exact_gap_raw.csv` / `_summary.csv` | — |
| Significance tests | `stat_tests.py` | `stat_tests.csv` | — |
| Schneider replication | `schneider_evrptw.py` + `schneider_bks_compare.py` + `plot_schneider_routes.py` | `schneider_evrptw_baseline.csv` / `schneider_evrptw_bks_comparison.csv` | `schneider_routes.png` / `schneider_vehcomp.png` |
| FSTSP reproduction | `week07_fstsp_repro.py` | `week07_fstsp_raw.csv` / `_summary.csv` | — |

Seed convention: all multi-seed experiments use fixed seed sets (GA uses `20260717/20260801/20260815/20260901/20261001`; W6/W7/W8 use consecutive seeds from `20260720`) for reproducibility; CSVs are excluded from the repo by design and regenerated locally via scripts + seeds.
