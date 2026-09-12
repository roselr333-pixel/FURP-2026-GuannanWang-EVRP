# Physical evaluator fix (W7/W8 re-run note)

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

## 4. One item left out this round

`week06_ground_air_evrp_tw.py` has its own `simulate`, which is a **parallel**
model (each sortie takes its landing time independently, with no serialisation
and no truck waiting) — looser even than the old `fstsp_simulate`. The W6
V0/V1/V2 headline and `week06_largeN` (scaling decay) go through that path and
were **not changed or re-run**, so "V2 vs V1 −424 (p=3.7×10⁻⁸)" and the scaling
decay 27.6%→12.1%→2.3% are still on the old model. Making this physical too and
re-running W6 is a clear follow-up.

## 5. Artifacts

- Change: `src/experiments/week07_fstsp_repro.py` (`fstsp_simulate` / `fstsp_simulate_multi`)
- Regression test: `tests/test_evaluators.py::test_heuristic_plans_are_physically_valid`
- Failure case: FC-7-4 in `docs/failure_cases_master.md` (now fixed)
- Re-run logs and CSVs under `src/results/`
