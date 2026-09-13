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
| 2-opt over greedy | 0–1.76% | **2.5–3.1%** |
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

Effects:

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
regression tests are listed in section 6.

Scope: the W6 headline, `week06_largeN` and the "V2 vs V1" row of
`stat_tests` were re-run. V0/V1 involve no drone and are bit-for-bit unchanged
(N=50 V1 is still 5661.9). `week06_sensitivity` and `week06_multi_objective`
go through `fstsp_makespan` and are unaffected. Old and new numbers are the last
five rows of section 3. The direction is unchanged as well: the benefit still
decays monotonically with scale, and now faster (only 3.4% left at N=50), so the
effective collaboration interval narrows to N ≤ 30.

## 5. Third round: drone-availability checks (V3 / W5 / M&C)

After the first two rounds a fourth instance of the same class of defect turned up:
**an evaluator that does not check, at launch time, whether the drone assigned to
a sortie is back on the truck**.

- `v3_ev_collab.ev_collab_k` already assigned sorties sequentially through
  `avail[d]`, but `launch = max(arr[i_pos], avail[d])` merely delayed the launch
  until the drone was free when it was not on board, although the truck had
  already left that node; `v3_greedy` also did not require sortie intervals to
  be disjoint. Measured: **40/40** V3 instances produced a physically invalid
  sortie set.
- The same defect was present in `week05_truck_drone_v2.simulate`
  (`drone_free = max(...)`, the same shape as the week06 evaluator of round 2),
  in `fstsp_mc.mc_simulate` (the M&C original-instance benchmark) and in
  `drone_scheduling.simulate` (the W8 scheduling experiment).

The fix: all four evaluators now require the drone to be on the truck at the
launch node (`avail[d] > arr[i_pos]`, or a recovery before its launch, is
infeasible), and `v3_greedy` gained a disjoint-interval pre-filter.

What changed on the re-run:

| Quantity | Old | New |
|---|---|---|
| V3 single-drone LNS reduction (K=1) | 34.7%~53.4% | **33.5%~52.4%** |
| V3 greedy (V3g) reduction | 27.9%~46.4% | **16.3%~39.2%** |
| V3 ablation: multi-customer gain (N=8/12/16/20, pp) | +16.4 / +19.4 / +9.5 / +1.7 | **+12.5 / +8.5 / +10.9 / −2.8** |
| W5 v2 flexible makespan (6 customers) | 277.3 (−49.8% vs truck-only) | **318.9 (−17.9%)** |

The W5 row also exposed two related problems: `depot_only_drone` timed the drone
with the *truck* speed and used a different tour construction from
`week05_truck_drone.py`, so the same baseline was reported as 389.5 in one script
and 270.6 in the other; both are fixed and the two scripts now agree (270.6). Note
that under the corrected single-drone schedule the W5 "any-node" variant is
**slower** than v1's depot-loop model on that six-customer instance (318.9 against
270.6) — the carried-drone model pays off at the larger sizes of W6-W8.

The direction is unchanged: the V3 collaboration gain is still substantial (K=1
33.5%~52.4%, K=2/3 up to 44.5%~72.5%), and the V3 ablation still points at
multi-customer ability as the main gain source (+8.5 to +12.5pp, turning to −2.8pp
at N=20).

## 6. Artifacts

- Round 1 change: `src/experiments/week07_fstsp_repro.py` (`fstsp_simulate` / `fstsp_simulate_multi`)
- Round 1 regression test: `tests/test_evaluators.py::test_heuristic_plans_are_physically_valid`
- Failure case: FC-7-4 in `docs/reference/failure_cases_master.md` (now fixed)
- Round 1 re-run logs and CSVs under `src/results/` (`week07_*`, `week08_*`, `week06_sensitivity*`, `week06_multi_objective*`, `stat_tests*`)
- Round 2 change: `src/experiments/week06_ground_air_evrp_tw.py` (`simulate` / `collaborative` / `run_variant` / summary columns)
- Round 2 regression tests: `tests/test_evaluators.py::test_w6_evaluator_rejects_overlapping_sorties`, `::test_w6_evaluator_rejects_out_of_range_sortie`, `::test_w6_truck_waits_for_a_late_drone`, `::test_w6_evaluator_matches_shared_fstsp_evaluator`, `::test_w6_collaborative_plan_is_physically_executable`
- Round 2 re-run logs and CSVs: `src/results/week06_ground_air_*`, `week06_largeN_*`, `stat_tests*`
- Round 3 change: `src/experiments/v3_ev_collab.py` (`schedule_inf` in `ev_collab_k` + the interval pre-filter in `v3_greedy`), `week05_truck_drone_v2.py`, `fstsp_mc.py`, `drone_scheduling.py`
- Round 3 regression tests: `tests/test_evaluators.py::test_v3_rejects_overlapping_sorties`, `::test_v3_greedy_produces_a_feasible_schedule`, plus `tests/test_truck_drone.py` for the W5 and M&C evaluators (`::test_v2_rejects_sortie_that_launches_while_drone_is_airborne`, `::test_v2_truck_waits_for_a_late_drone`, `::test_mc_rejects_sortie_that_launches_while_drone_is_airborne`, `::test_mc_evaluator_matches_shared_fstsp_evaluator_on_random_plans`, `::test_depot_only_baseline_agrees_across_week05_scripts`)
- Failure case: FC-7-5 in `docs/reference/failure_cases_master.md`
- Round 3 re-run logs and CSVs: `src/results/v3_ev_collab_*`, `v3_ablation_*`, `week05_truck_drone_v2_output.txt`
