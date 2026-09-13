# Progress Report — FURP 2026 EVRP

> Student self-assessment, written 2026-07-24 by Guannan Wang.
---

## 1. What the project asks for

### 1.1 Core positioning

Both the outline and the README repeat one idea: **the goal is not a world-class solver, but a reproducible research workflow** — understand a problem variant → run a reliable baseline → evaluate feasibility and cost → test one improvement with fair comparisons. This framing makes "solid, fair comparison" matter far more than "number of algorithms implemented".

### 1.2 Six learning objectives

1. Explain CVRP, VRPTW, EVRP-TW, and truck-drone routing.
2. Reproduce one baseline solver or learned policy.
3. Report objective value, feasibility, constraint violations, and runtime together.
4. Diagnose why a route becomes infeasible or inefficient.
5. Implement one focused improvement or constraint extension.
6. Present one reproducible optimization experiment with clear evidence.

### 1.3 Eight-week plan and stage deliverables

| Week | Theme | Expected deliverable |
|---|---|---|
| 1 | Environment & baseline | a solved small instance |
| 2 | Literature & problem variants | reading notes + constraint map |
| 3 | Reproduce a baseline | objective, feasibility, runtime logs |
| 4 | EVRP-TW constraints | time-window & energy violation table |
| 5 | Truck-drone formulation | modeling note + synchronization rules |
| 6 | Hybrid / learning method | demo run on small instances |
| 7 | Improvement & ablation | fair comparison vs baseline |
| 8 | Final integration | report, slides, demo video, reproducibility package |

### 1.4 Grading weights

- 25% reproducibility & engineering quality;
- 25% baseline-vs-improved comparison quality;
- 20% failure / constraint-violation analysis depth;
- 30% final report, demo, and technical explanation.

The final report/demo alone is 30%, while the fair-comparison segment is another 25% — and that comparison used to be my weakest point until recently (see §2.2).

### 1.5 Hard reporting standard

The metrics spec requires: compare baseline and improved method on at least 3 instance sizes or 3 representative instances; report objective, feasibility, runtime, hardware, random seeds, and solver parameters together (never "shortest distance" alone); include at least 3 failure cases with constraint-level diagnosis.

### 1.6 The focused question I converged on

The project page says a good SEP project revolves around one focused question. Mine is **Ground-air collaborative EVRP-TW**, stated as:

> When a ground electric fleet and a drone deliver cooperatively, both under battery and charging constraints, how much does the collaboration reduce makespan relative to a pure ground EV fleet, and which constraints (drone range, time windows, synchronization) bound the gain?

Every experiment I run speaks to this question.

---

## 2. Current progress

### 2.1 Overview (requirement → status → reading)

| Requirement | My status | Reading |
|---|---|---|
| Explain the four problem classes | CVRP / VRPTW / EVRP-TW / truck-drone all coded | met |
| Reproduce a baseline | OR-Tools on Solomon 56 (56/56 feasible, avg gap 7.2%) + self-written GA (5-seed check, avg gap 36.6%±15.8%) + **reproduced Murray & Chu 2015 FSTSP heuristic** + **reproduced Schneider 2014 E-VRPTW** (18 BKS instances, mean distance gap down to +21.3%) | met; only the Schneider reading note is still pending |
| Report objective/feasibility/violations/time | all scripts emit these fields | met; GA now has a 5-seed check |
| Diagnose infeasibility/inefficiency | FC1–FC4 constraint-level failure table | met |
| One focused improvement | truck-drone multi-customer extension (V2), 8.5–22.3% shorter than published baseline | met |
| Reproducible evidence | scripts + logs + fixed seeds present | met |
| W6 hybrid-method demo | V0/V1/V2 unified workflow, 40 instances (4 sizes × 10 seeds) + Integration Note | met |
| W7 improvement + ablation | 5-config ablation with clear attribution | met |
| W8 report/slides/video/package | not started | **gap (30% of grade)** |

### 2.2 What is actually done

- **W1 environment & baseline**: OR-Tools solves small CVRP/VRPTW instances; environment, dependencies, and venv are recorded (`docs/reference/env_record.md`).
- **W2 literature**: one survey note (Erdelić & Carić 2019) finished; the FSTSP foundational paper note was also written during reproduction. The planned third paper (Schneider 2014) is still missing.
- **W3 baseline reproduction**:
  - OR-Tools on the official Solomon 56 set: 56/56 feasible, average gap 7.2% vs BKS;
  - self-written GA (permutation coding + Solomon I1 insertion decoding + OX crossover + tournament + elitism): 56/56 runs complete; 5-seed check gives avg gap 36.6%±15.8% (best-of-5 31.2%) — reported as weaker than OR-Tools, a "self-built baseline" rather than an improvement.
- **W4 EVRP-TW constraints**: electric-vehicle + charging experiments done, and charging count / charging time / energy violations are reported inside the later week06 script, but not yet assembled into a dedicated scoring-facing violation table.
- **W5 truck-drone formulation**: v2 lets the drone ride the truck and launch/recover at any node; on a small instance it is 17.9% shorter than truck-only. Under a physical single-drone schedule it is 17.8% slower than v1's depot-only model (270.6) on that six-customer instance: a carried drone has to be recovered by the truck and can fly one sortie at a time, and that overhead is only repaid at larger sizes (W6-W8).
- **W6 hybrid method (Track B)**: one greedy core runs V0 (truck-only, no EV) / V1 (truck EV baseline) / V2 (collaborative EV). 4 sizes (8/12/16/20) × 10 seeds = 40 instances, all feasible; V2 improves over V1 by **42–55%** on average, with a 65–72% average offload rate. The Week 6 Integration Note (Track B, 4 sections, EN+ZH) is written.
- **P1 paper reproduction (Murray & Chu 2015 FSTSP)**: implemented the paper's Section 3.3 insertion heuristic and ran it head-to-head with my V2 on the same 40 instances under the same serial-drone evaluator — my multi-customer extension averages **8.5–22.3%** shorter than the published heuristic, and cap3 goes further at **11.4–28.2%** shorter. This is the "published baseline → my extension" fair comparison the project page asks for.
- **W7 improvement + ablation**: five configurations vary only two knobs (max customers per flight / whether a stop may host multiple launches). The V2 gain over baseline decomposes into: multi-customer ability (+6.6~+17.7pp, main source), multi-takeoff (+4.1~+7.3pp, secondary), and cap3 further (+2.3~+8.7pp). `abl_cap1` matches `published` exactly, proving the framework correctly degrades to the published heuristic when multi-customer is switched off (sanity check passed).

### 2.3 Reproducibility evidence already in place

Code, per-instance raw CSVs, size-aggregated average tables, run logs, and fixed seeds (early `20260717`, later `20260720` base) all live under `src/experiments/` and `src/results/`. This base for the 25% "reproducibility" slice already exists.

---

## 3. What can still be optimized or improved

Ordered by grading impact and by how readily each can be closed, in four groups.

### 3.1 Highest impact, do first

1. **W8 deliverables are entirely missing (30% of grade)**: final report, 5–8 minute demo video, slides, and reproducibility package are not started. This is the single largest gap; I should build the skeleton now rather than wait for week 8.
2. ~~**Schneider 2014 (E-VRPTW) reproduction still pending**~~ ✅ **Delivered**: `schneider_evrptw.py` (+ `schneider_improve.py`) solves the 92 original instances with a constructive greedy plus local search and compares 18 of them against the published BKS — mean distance gap **+21.3%** (was +52.7% for the construction alone), vehicles 3.28 vs 2.06. Details in `docs/baselines/schneider_evrptw_replication_en.md`. Only the reading note (no PDF access) is still missing.

### 3.2 Metric and rigor gaps

3. ~~**No centralized config / parameter document**~~ ✅ **Delivered**: `docs/reference/configs_and_parameters.md`, a single page with the global instance construction, OR-Tools params, GA params, ground-air / FSTSP params, random-seed conventions, and path conventions. Directly closes the 25% reproducibility line.
4. ~~**EVRP-TW charging breakdown not tabled separately**~~ ✅ **Delivered**: `docs/analysis/evrp_tw_charging_detail.md`, pulled from `week06_ground_air_results.csv` (40 instances). It gives four views: mean recharge count, recharge-time share, sync-rejected count after recharge, and battery-cost decomposition (V0 vs V1 vs V2). The most informative slice is "V0 vs V1 battery cost = 12–20%, but V2 is still 31–49% shorter than V0" — it quantifies *how much coordination is worth* in the EVRP-TW setting.
5. ~~**Failure cases are scattered**~~ ✅ **Delivered**: `docs/reference/failure_cases_master.md`, a uniform 7-field template (instance / solver / objective / feasible / violated constraint / where it first breaks / next fix). Merges FC1–FC4 (W6 constraint failures) + FC-S1~FC-S4 (W3/W4/W5 weak results, including C103 90.6% gap, RC2 family 55.1% mean gap) + FC-7-1/FC-7-2 (W7 sanity-check bugs already fixed). 17 entries in total; **strictly infeasible appears only once (FC-1)** — everything else is "longer-than-BKS distance", "tight-constraint violation", or "implementation bug (now fixed)".
6. ~~**Early experiments used a single seed**~~ ✅ **Partially delivered**: see §3.2-supplement below.

#### 3.2-supplement: distinguishing which baselines really need multi-seed

This is the addendum to item 6 above. I re-walked the W1–W5 baselines — **only one is truly stochastic and demands multi-seed**; the other four are either OR-Tools runs (whose spread is search noise with no controllable seed) or fixed-instance demos with no comparable random source.

| W | Script | Stochastic? | Needs multi-seed? | Status |
|---|---|---|---|---|
| W1 | `week01_baseline.py` | no (fixed 6-customer hand route) | no | OK |
| W2 | (no W2 script) | — | — | — |
| W3 | `week03_experiment.py` / `benchmark_solomon_vrptw.py` | OR-Tools (no controllable seed; run-to-run search noise) | no | OK |
| W4 | `week04_evrp_tw.py` / `benchmark_evrptw.py` | OR-Tools (no controllable seed; run-to-run search noise) | no | OK |
| W5 | `week05_truck_drone.py` / `_v2.py` | fixed 6-customer hand/heuristic | no (no comparable random source) | OK |
| W3-W5 | `baseline_ga_vrptw.py` | **GA stochastic** | **yes** | **Done — re-run with 5 seeds; columns `ga_dist_mean / ga_dist_best / ga_veh_best / ga_gap_mean_pct / ga_gap_std_pct / n_seeds` added to `baseline_ga_vrptw_results.csv`** |

**Conclusion**: the "multi-seed W1–W5" gap is really only GA. The other four are OR-Tools runs or fixed demos with no controllable random variable; OR-Tools is time-budgeted rather than bit-reproducible, but repeating it would only measure search noise, so only the GA was re-run with seeds.

##### GA 5-seed check (done)

I ran the self-written GA on all 56 Solomon instances with 5 fixed seeds (`20260717 / 20260801 / 20260815 / 20260901 / 20261001`), recording per-instance mean, best, and seed-to-seed std in `baseline_ga_vrptw_results.csv` (six new columns).

| Metric (gap to BKS) | Value |
|---|---:|
| Cross-instance seed-mean gap | **36.6%** (std across instances 15.8%) |
| Cross-instance best-of-5 gap | **31.2%** |
| Within-instance seed spread (mean std) | **3.9 pp** |
| Solved | 56/56 feasible |

Per family (seed-mean gap): C1 25.9%, C2 36.0%, R1 31.2%, R2 41.5%, RC1 30.6%, RC2 56.8%.

Notes:
- The earlier "~36.2%" was a **single-seed** figure; the 5-seed check gives **36.6%**, essentially the same — my GA is fairly stable, with a within-instance seed spread of only 3.9 pp on average.
- This is not an improvement, just a statistically sounder check of an existing baseline: I now report mean±spread instead of one random run. Best-of-5 (31.2%) sits ~5 pp below the mean, normal GA variance.
- The GA is still clearly weaker than OR-Tools (7.2%); its role is unchanged — a baseline I implemented to understand the evolutionary operators, not a SOTA attempt.
- Fixed a latent bug: the old `main()` called `random.seed()` outside the loop, polluting the global RNG and making "multi-seed" meaningless; it now reseeds only inside `solve_ga(seed=...)`, so the five runs are genuinely independent.

### 3.3 Methodological and scientific upgrades

7. ~~**Instance sizes are small**~~ ✅ **Partially delivered**: `src/experiments/week06_largeN.py` extends to **N=30 and N=50** (5 seeds each), outputs `week06_largeN_summary.csv`. **Important finding**: the V2 advantage **monotonically shrinks with scale** —

   | Size | V2 vs V1 (was) | V2 vs V1 (now added) |
   |---|---:|---:|
   | N=8  | 50.5% | (unchanged) |
   | N=12 | 55.3% | (unchanged) |
   | N=16 | 53.9% | (unchanged) |
   | N=20 | 42.1% | (unchanged) |
   | **N=30** | — | **27.6%** |
   | **N=50** | — | **12.1%** |

   Why: at N=50, V1 (with battery + recharge) costs 5670 vs V0 (no battery) at 3094 — the battery constraint alone nearly doubles the truck's makespan when N grows, and V2's drone can only "bypass" a limited amount of charging-path detour. So the drone's coordination benefit is diluted by the structural battery cost. This is more interesting than "I scaled to 50 customers" because it *quantifies the diminishing returns of coordination* — exactly the kind of limitation analysis the project page rewards. All 10 instances at N=30 and N=50 remain 100% feasible; sync-rejected jumps from ~15k (N=20) to 4.5 million (N=50) — the rendezvous constraint genuinely becomes the bottleneck at scale, which is genuine evidence that the synchronization model is doing real work.

8. ~~**Greedy with no local search**~~ ✅ **Partially delivered**: `src/experiments/week07_fstsp_repro.py` now defines `my_v2_fstsp_with_2opt(inst, max_passes=10)` — an intra-route 2-opt post-processor on the V2 truck route, accepting only moves that **strictly improve makespan**. Results across 40 instances:

   | Size | V2 makespan | V2 + 2-opt makespan | 2-opt gain | avg 2-opt moves per instance |
   |---|---:|---:|---:|---:|
   | N=8  | 256.0 | 247.7 | **+2.98%** | 1.0 |
   | N=12 | 412.1 | 400.2 | **+3.07%** | 1.3 |
   | N=16 | 554.4 | 533.9 | **+3.08%** | 2.1 |
   | N=20 | 767.2 | 746.3 | **+2.49%** | 1.9 |

   **Conclusion**: 2-opt adds only 2.5–3.1% on top of V2. The reason: by the time V2 has offloaded the long-distance customers to the drone, the remaining truck route is already near a near-linear shape, leaving little room for 2-opt. This is both good and bad news — good that my heuristic already approaches the current-neighborhood local optimum; bad that "distance to global optimum" remains unquantified (would need MILP upper bounds or wider neighborhoods like 3-opt / or-opt to close). I will come back to this later.

9. ~~**Max 2 (sometimes 3) customers per flight**~~ — **Not done** (enumeration cost). After this round, since 2-opt barely moves anything, raising the per-flight cap to 3+ would mostly re-explode the O(n⁴) enumeration. **Deferred** to later work alongside efficiency optimizations for larger neighborhoods.

10. **Only 2/3 reading notes done**: survey + FSTSP written; Schneider 2014 pending a PDF.
11. **Track C/D (RL/DL) not attempted**: acceptable per the lab (needs data and repeated runs first), but I will state in the final report, in a sentence or two, why it is deferred.

### 3.5 Deepening stage (W6–W7 completed, 2026-09-10)

14. ~~**No domain-standard solver baseline (PyVRP)**~~ ✅ **Delivered**: `baseline_pyvrp_vrptw.py` runs PyVRP 0.14.0 on all 56 Solomon instances, mean gap **−3.0%** (beats BKS); consolidated with OR-Tools (+7.2%) and own GA (+36.6%±15.8%) in `baseline_consolidated.py` → `baseline_consolidated.csv` + `baseline_consolidated.png` / `pyvrp_family_gap.png`. The three baselines are clearly positioned (PyVRP strongest → BKS → OR-Tools → GA), no overclaiming.
15. ~~**Sensitivity reported as single values, no error bars**~~ ✅ **Delivered (with bug fix)**: `week06_sensitivity.py` upgraded to 5-seed mean ± std with error-bar figures. On 2026-09-10 a bug was fixed where the drone-range R parameter was not passed to the model (R sweep was flat at 50.5%); after the fix R 60→200 gives 15.5%→27.7%→35.2%→50.5%@160→48.7%@200 (saturates after 160), matching the depth doc. Q/K/N sweeps unchanged.
16. ~~**Multi-objective computed at a single point**~~ ✅ **Delivered**: `week06_multi_objective.py` sweeps weights w∈{0,0.25,0.5,0.75,1.0} (5 seeds). V2 (215.2, 415.7) vs V1 (486.4, 622.4): distance −56%, makespan −33%, dominating on both axes; labelled a "coarse front" (weighted-sum greedy, not a full Pareto solver).
17. ~~**No coherent "why it works" chain**~~ ✅ **Delivered**: `docs/analysis/week06_depth_analysis_zh.md` chains the ablation (multi-customer ability as main source, +6.6~17.7pp), the sensitivity K scan (25.3%→56.5%), the applicability regime, two-axis MO dominance, three-baseline positioning, failure cases (N=50 ~4.5M sync rejections), and limitations into one argument; accompanied by `docs/reference/experiment_evidence_index_zh.md` and `experiment_evidence_index_en.md` collecting every citable number with provenance.
18. ~~**The collaborative heuristic had no improvement phase**~~ ✅ **Delivered**: `src/experiments/week08_lns.py` adds a destroy-and-repair LNS on top of the greedy V2; over 60 instances (10 seeds × N=8/12/16/20/30/50) it improves the greedy by a consistent **+9% to +12.6%** (paired Wilcoxon overall p=3.6×10⁻⁹) and lifts the N=50 collaboration benefit from the greedy's 17.6% to 28.1%. `src/experiments/stat_tests.py` adds a significance test for every headline pairing (my V2 vs published M&C, the two ablation factors, LNS vs greedy, V2 vs V1). Figure `figures/lns_vs_greedy.png`.
19. ~~**Single drone only**~~ ✅ **Delivered**: `src/experiments/week08_multidrone.py` supports K parallel serial drones (K=1 numerically identical to the single-drone evaluator); K=1/2/3 over the same 60 instances lifts the benefit vs truck-only from 28.1% to 36.0% at N=50 and from 45.5% to 69.6% at N=8, raising the whole scaling-decay curve; the LNS still adds +5% to +14% at every K (Wilcoxon K=3 vs K=1 overall p=1.67×10⁻¹¹). Figure `figures/multidrone.png`.
20. ~~**random-geometry instances + K≤3 + simple schedule**~~ ✅ **Delivered**: `src/experiments/week08_multidrone_std.py` builds 16 standard instances from official Solomon topologies (C101/C201/R101/RC101) and extends K to 5 (48.6%~71.4% at K=5); `src/experiments/drone_scheduling.py` treats the sortie-to-drone assignment as an explicit schedule (greedy / local / exact optimal), showing the naive rule is only +0.081% above the exact optimum (max 3.2%) with local search gaining just +0.001% -- the simple rule is already near-optimal. Figure `figures/multidrone_std.png`.

21. ~~**The drone had no energy or payload model**~~ ✅ **Delivered**: `drone_energy.py` gives the drone a payload capacity and a payload-dependent energy budget (`BETA` swept 0 → 0.04); `drone_energy_ablation.py` re-runs the core ablation under it (multi-customer gain +10.4 → +6.1 pp, while the energy-unaware published heuristic is only 42–48% feasible), and `drone_energy_mainline.py` puts the same gates on the V3 and W8 evaluators — the gains survive there (V3 K=1 33.5–53.0%, K=3 up to 72.4%) for 1.5–8.1% more makespan. Both evaluators keep the range-only model as the default, so the earlier numbers are unchanged.

22. ~~**"How far is the heuristic from the optimum" was only answered at n=8**~~ ✅ **Delivered**: `cpsat_fstsp.solve_exact` now takes a warm start (`upper_bound` + `AddHint`), and `week08_exact_gap.py` runs n=8/10/12/14/16 x 5 seeds. The n=8 optimum is reproduced exactly (greedy +31.2%, LNS +16.5%); the warm start returns a feasible plan on 23/25 instances where the cold search could return none; from n=10 on CP-SAT's own plan is **8.8-17.5% below my best heuristic plan**, while its certified dual bound stays at 0, so optimality is unprovable there without a stronger relaxation.

### 3.4 Engineering and delivery

12. **No git commit / push yet**: everything is still local; the reproducibility package only counts once it is committed.
13. **No "someone else can rerun this" README / reproduction guide**: environment, commands, seeds, and parameters belong in one place.

---

## 4. What I will do next, in priority order

- **P0 (this week)**: ① build the W8 skeleton — final-report framework + slide outline + demo-video script (even if empty at first); ② git commit/push the current files.
- **P1** ✅: reproduced Schneider 2014 (E-VRPTW) as a second published baseline — 92 instances, 18 with published BKS, mean distance gap +21.3% after the local search.
- **P2**: write a centralized config/parameters document; assemble the EVRP-TW charging breakdown and the W3/W4 weak results into one failure table; add a "reproducible by others" README.
- **P3**: scale instance sizes (medium/large) + add local search or MILP bounds; raise the per-flight customer cap.

---

## 5. Summary

The main line (Ground-air collaborative EVRP-TW) has come together end to end: from baselines (pure-truck EV, OR-Tools, the published FSTSP heuristic) to the improvement (multi-customer + multi-takeoff V2) to a controlled ablation — the evidence chain is complete and reproducible. The two things still genuinely missing are **packaging the work into W8 deliverables** and **finishing the Schneider (2014) reading note** (the reproduction itself is now in place). Once those are closed, the four grading dimensions can each rest on a concrete deliverable.

Related files: `src/experiments/` (weekly scripts), `src/results/` (per-instance and aggregated CSVs), `docs/` (weekly reports and notes), `learning_guide/papers/` (reading notes).
