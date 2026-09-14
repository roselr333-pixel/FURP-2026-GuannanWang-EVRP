# Documentation index

Everything I wrote for this project, grouped by role. Every experiment exists as
two independent documents, one English and one Chinese; they are written
separately, not translated from each other.

## Final report

| Document | What it holds |
|---|---|
| `report/final_experimental_report_zh.md` | the final experimental report: problem definition, the two replicated papers, model, methods, experiment setup, results (baselines, main line, ablation, standard instances, scale, LNS/ALNS, multi-drone, V3, capacity, energy, exact optimum, Schneider), failure analysis, discussion, conclusions, and the four metric tables plus a route-output appendix |

## Reference

| Document | What it holds |
|---|---|
| `reference/experiment_evidence_index_en.md` / `_zh.md` | every citable number with its source, plus the caveat that goes with it |
| `reference/formal_model_zh.md` / `_en.md` | the model in standard notation: sets, parameters, variables, objective, hard vs soft constraints, what is not modelled, and where each part sits in the code |
| `reference/failure_cases_master.md` | 13 constraint-level failure cases (FC-S1 to FC-7-5) |
| `reference/configs_and_parameters.md` | instances, solver settings, seeds, path conventions |
| `reference/env_record.md` | hardware and software environment |

## Analysis

| Document | What it holds |
|---|---|
| `analysis/week06_depth_analysis_en.md` / `_zh.md` | the "why it works / when it works" chain: ablation, sensitivity, applicability window, multi-objective, baselines, failure cases, limitations |
| `analysis/evaluator_physical_fix_note_en.md` / `_zh.md` | what the physical-evaluator fix changed, in two rounds, and old vs new numbers |
| `analysis/progress_report.md` / `_zh.md` | mid-project self-review, written 2026-07-24; its experiment numbers predate the evaluator fix |
| `analysis/evrp_tw_charging_detail.md` | charging counts, charging time share and the battery cost, week-06 data |

## Weekly notes and per-experiment notes

| Document | What it holds |
|---|---|
| `weekly/0-5_weekly.md` / `_zh.md` | weekly progress log, weeks 1-5 |
| `weekly/week01_checkpoint.md`, `weekly/week03_report.md`, `weekly/week05_checkpoint.md` / `_zh.md` | early checkpoint notes |
| `weekly/week06_ground_air_report.md` / `_zh.md` | week 6: ground-air collaborative EVRP-TW, v2 iteration |
| `weekly/week06_integration_note.md` / `_zh.md` | week 6 integration note: model framing and the V0/V1/V2 comparison |
| `weekly/week07_fstsp_repro_report.md` / `_zh.md` | Murray & Chu (2015) FSTSP replication, and my V2 on the same instances |
| `weekly/week07_ablation_report.md` / `_zh.md` | the five-configuration ablation on the synthetic instances |
| `weekly/week07_ablation_std_note_en.md` / `_zh.md` | the same ablation on official Solomon topologies |
| `weekly/week08_lns_note_en.md` / `_zh.md` | destroy-and-repair LNS on top of the greedy |
| `weekly/week08_multidrone_note_en.md` / `_zh.md` | K = 1/2/3 drones on the synthetic instances |
| `weekly/week08_multidrone_std_note_en.md` / `_zh.md` | standard instances, K up to 5, explicit sortie scheduling |
| `weekly/week08_exact_gap_note_en.md` / `_zh.md` | exact optimum by CP-SAT, the heuristic gaps, and what a warm start does to the primal/dual boundary |
| `weekly/week08_alns_note_en.md` / `_zh.md` | ALNS on the physical FSTSP model: whether the search side closes the gap the exact study exposed |
| `weekly/week08_mc_benchmark_note_en.md` / `_zh.md` | the paper's original Murray & Chu test instances |
| `weekly/v3_ev_collab_note_en.md` / `_zh.md` | V3: electric truck + drone + charging stations + time windows |
| `weekly/v3_ablation_note_en.md` / `_zh.md` | the same core ablation under EV + time windows |
| `weekly/drone_energy_note_en.md` / `_zh.md` | drone energy and payload model (extension): what it does to the ablation, and what it does to V3 and the K-drone W8 runs |

## Baselines and replications

| Document | What it holds |
|---|---|
| `baselines/ga_baseline_report.md` / `_zh.md` | my own GA baseline, multi-seed against BKS |
| `baselines/schneider_evrptw_replication_en.md` / `_zh.md` | Schneider (2014) E-VRPTW replication |

## Reading and meetings

- `meeting_notes/` — supervision meeting notes
- `paper note/` — paper reading notes
