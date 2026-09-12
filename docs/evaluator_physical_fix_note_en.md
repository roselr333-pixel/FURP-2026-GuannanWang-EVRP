# Physical evaluator fix (W7/W8 + W6 re-run note)

## 1. What changed

`week07_fstsp_repro.fstsp_simulate` (and its multi-drone form
`fstsp_simulate_multi`) is the completion-time evaluator shared by the W7/W8
truck-drone experiments. The original serialised sorties with a `drone_avail`
chain but **never checked that the drone was back on the truck**: when one sortie
was nested inside another (A flies 0 → 2 while B launches and recovers in between
at 12 → 10) it still returned a makespan, although no plan can fly two
overlapping sorties with one drone.

The evaluator now enforces physical validity:

- the launch node must be ahead of the recovery node on the truck route;
- each sortie's flight length is within the drone range `R_D`;
- the drone must be back on the truck when the truck reaches the launch node;
- if any of these fails the plan is infeasible and **inf** is returned instead
  of a makespan.

Because every heuristic (`my_v2_param`, `fstsp_insertion`, the LNS) tests a
candidate move with this evaluator, an inf result makes the move **auto-rejected**,
so the solutions they produce are physically valid by construction.

## 2. Scope

Every experiment routed through `fstsp_makespan` / `fstsp_makespan_multi` is
affected and was re-run: `week07_fstsp_repro`, `week07_improvement_ablation`,
`week08_lns`, `week08_multidrone`, `week08_multidrone_std` (including
`week08_scheduling.csv`), `week06_sensitivity`, `week06_multi_objective`,
`stat_tests`, and the "original V2" column of `week08_exact_gap`. The dependent
figures (`lns_vs_greedy`, `multidrone`, `multidrone_std`, `sensitivity_panels`,
`mo_*`) were regenerated.

## 3. Old numbers → new numbers

| Quantity | Old (non-physical) | New (physical) |
|---|---|---|
| V2 vs Murray & Chu (2015), W7 | 8–22% shorter | **10.2–14.2% shorter** |
| V2 vs truck-only (ablation, N=8/12/16/20) | 39.2 / 37.8 / 32.4 / 29.9% | **34.5 / 29.0 / 28.7 / 24.8%** |
| multi-customer gain | +6.6~17.7 pp | **+8.6~12.1 pp** |
| multi-takeoff gain | +4.1~7.3 pp | **+2.2~4.4 pp** |
| `abl_cap1 == published` (sanity check) | passes | **still passes (per-instance equality)** |
| LNS over greedy | +9~12.6% | **+12.5~21.3%** |
| 2-opt over greedy | 0–1.76% | **1.97–3.22%** |
| Multi-drone (N=50, K=1 → K=3, vs truck) | 28.1% → 36.0% | **29.5% → 38.1%** |
| Standard instances (N=10 / N=50, K=5) | 71.4% / 48.6% | **71.4% / 46.8%** |
| Scheduling: configs where naive is provably optimal | 31/64 | **64/64** |
| Scheduling: local-search gain over naive | +0.001% | **0.000%** |
| Wilcoxon: V2 vs published M&C | n=40, −73.0, p=5.9×10⁻⁷ | **n=38, −73.2, p=2.4×10⁻⁷** |
| Wilcoxon: LNS vs greedy | n=46, −146.2, p=3.6×10⁻⁹ | **n=54, −194.3, p=1.7×10⁻¹⁰** |
| Sensitivity: battery Q (120→500) | 55.8% → 47.1% | **41.2% → 29.7%** |
| Sensitivity: range R (60→160→200) | 15.5% → 50.5% → 48.7% | **15.4% → 34.4% → 34.4%** |
| Sensitivity: customers/sortie K (1→3) | 25.3% → 50.6% → 56.5% | **20.5% → 34.4% → 37.1%** |
| Multi-objective: distance / makespan (V2 vs V1) | −56% / −33% | **−32% / −34%** |
| W6 headline V2 vs V1 (N=8/12/16/20) | 50.5 / 55.3 / 53.9 / 42.1% | **33.6 / 24.5 / 19.6 / 15.6%** |
| W6 offload rate (N=8/12/16/20) | 65.0 / 70.8 / 71.9 / 67.0% | **31.2 / 21.7 / 18.1 / 14.5%** |
| Scaling decay, V2 vs V1 (N=30/50/100) | 27.6% → 12.1% → 2.3% | **8.6% → 3.4% → 0.5%** |
| Scaling decay, offload rate (N=30/50/100) | 62.0% → 42.8% → 23.4% | **11.3% → 5.2% → 2.6%** |
| Wilcoxon: V2 vs V1 (collaborative vs EV) | n=40, −424.3, p=3.7×10⁻⁸ | **n=40, −182.1, p=3.71×10⁻⁸** |

Takeaways:

- **The direction is unchanged; the magnitudes are smaller.** V2 still beats the
  published M&C heuristic (10–14%), and the ablation attribution (multi-customer
  capability is the main gain source) still holds; `abl_cap1` still equals
  published exactly on every instance.
- **The scheduling section changes character.** After the fix the sortie sets are
  non-overlapping, so with K drones there is no contention and the naive
  "earliest-available" rule is provably optimal on all 64 configs with zero local
  gain. The earlier "31/64 + a small local gain" was a false contention created by
  nested sorties.
- The two largest downward revisions are battery sensitivity (55.8%→41.2%) and
  the multi-objective distance axis (−56%→−32%), both of which depended directly
  on the optimistically low makespans.

## 4. Second round: the week06 evaluator (same day)

`week06_ground_air_evrp_tw.py` had its own `simulate`: it took each sortie's
landing time independently (`drone_free = max(...)`), never checked that the drone
was back on the truck and never serialised sorties, so nested or crossing sorties
were given a makespan too — looser than the pre-fix `fstsp_simulate`. The W6
V0/V1/V2 headline and `week06_largeN` (scaling decay) ran through that path.

This round puts it on **the same physical model as `fstsp_simulate`**:

- sorties are processed in launch-position order;
- a launch must precede its recovery on the truck route;
- a sortie's flight stays within `R_D`;
- a sortie cannot start before the previous one has been recovered (one drone
  flies one sortie at a time);
- if the drone arrives late the truck waits at the recovery node, and the wait
  shifts every later arrival;
- any violation returns `inf`.

In the same change, `collaborative` accepts a sortie only when **the makespan of
the whole physical plan improves** (previously: when removing the customers
shortened the *truck* route), and candidate sorties are checked against the
single-drone route positions. Together these keep the heuristic from producing
plans the evaluator would reject: the re-run reports
`V2_plan_valid_rate = 1.0` at every size.

Cross-validation: over 400 random routes with random sortie sets,
`week06_ground_air_evrp_tw.simulate` and `week07_fstsp_repro.fstsp_simulate`
return the same makespan, including the same infeasibility verdicts; the
regression tests are listed in section 5.

Scope: the W6 headline, `week06_largeN` and the "V2 vs V1" row of
`stat_tests` were re-run. V0/V1 involve no drone and are bit-for-bit unchanged
(N=50 V1 is still 5661.9). `week06_sensitivity` and `week06_multi_objective`
go through `fstsp_makespan` and are unaffected. Old and new numbers are the last
five rows of section 3. The direction is unchanged as well: the benefit still
decays monotonically with scale, and now faster (only 3.4% left at N=50), so the
effective collaboration interval narrows to N ≤ 30.

## 5. Artifacts

- Round 1 change: `src/experiments/week07_fstsp_repro.py` (`fstsp_simulate` / `fstsp_simulate_multi`)
- Round 1 regression test: `tests/test_evaluators.py::test_heuristic_plans_are_physically_valid`
- Failure case: FC-7-4 in `docs/failure_cases_master.md` (now fixed)
- Round 1 re-run logs and CSVs under `src/results/` (`week07_*`, `week08_*`, `week06_sensitivity*`, `week06_multi_objective*`, `stat_tests*`)
- Round 2 change: `src/experiments/week06_ground_air_evrp_tw.py` (`simulate` / `collaborative` / `run_variant` / summary columns)
- Round 2 regression tests: `tests/test_evaluators.py::test_w6_evaluator_rejects_overlapping_sorties`, `::test_w6_evaluator_rejects_out_of_range_sortie`, `::test_w6_truck_waits_for_a_late_drone`, `::test_w6_evaluator_matches_shared_fstsp_evaluator`, `::test_w6_collaborative_plan_is_physically_executable`
- Round 2 re-run logs and CSVs: `src/results/week06_ground_air_*`, `week06_largeN_*`, `stat_tests*`
