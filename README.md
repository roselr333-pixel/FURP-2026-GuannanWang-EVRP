# FURP-2026 · Guannan Wang · EVRP (ground-air collaborative EVRP-TW)

> **Faculty Undergraduate Research Practice (FURP)** · Research Track
> Faculty of Science and Engineering · University of Nottingham Ningbo China

This is my FURP project repository. I study **Electric Vehicle Routing with Time
Windows (EVRP-TW)** and extend it to **truck–drone collaboration**. The work
follows a reproducible workflow: a solid baseline → one focused improvement →
fair comparisons against published baselines → constraint-level failure analysis.

---

## Project info

| Field | Entry |
|---|---|
| Student | Guannan Wang |
| Project title | EVRP — ground-air collaborative EVRP-TW |
| Project tag | EVRP |
| Track | Research |
| Supervising faculty | FOSE |
| Project lead | Dr. Tianxiang Cui |
| Team or individual | Individual |
| Cited papers replicated | Murray & Chu (2015) FSTSP; Schneider (2014) E-VRPTW |

**One-line summary.** Starting from a classical OR-Tools VRPTW baseline I add a
battery/charging dimension and time windows (EVRP-TW), build a truck–drone
collaborative model on top, and test one focused improvement — drone sorties that
serve several customers and truck stops that can be reused — with fair, seeded
comparisons against published baselines.

---

## What is in the repository

- **Baselines** (fair comparison anchor): OR-Tools, PyVRP, my own GA, all run on
  the official 56-instance Solomon VRPTW set against published BKS.
- **Two published replications**: Murray & Chu (2015) FSTSP (truck–drone) and
  Schneider (2014) E-VRPTW (electric + time windows).
- **One improvement with an ablation**: multi-customer drone sorties + stop
  reuse (V2), decomposed against single-customer and single-takeoff variants.
- **Improvement phase**: a destroy-repair LNS on top of the constructive greedy,
  with paired Wilcoxon significance tests.
- **Design-variable sweeps**: drone count (K=1/2/3/5), standard Solomon topology,
  drone-to-sortie scheduling (naive / local search / exact optimum) with an
  optimality lower-bound certificate.
- **EV + time-window collaboration** (V3): the week06 battery/charging/TW layer
  stacked back onto the truck–drone model, single and multi-drone.
- **Evidence layer**: an experiment evidence index, a failure-case catalogue, a
  parameter/settings sheet, and a one-command reproduction script.

---

## Repository map

```
README.md              this file
REPRODUCE.md           how to rerun everything + conclusion → script → artifact
run_all.py             one command to rerun all headline experiments
requirements.txt       pinned dependencies
docs/                  reports, notes, evidence index, failure cases
src/experiments/       all experiment code
src/tools/             plotting / dashboard helpers
src/results/           run logs (CSV outputs are regenerated locally)
figures/               figures used in the reports
tests/                 pytest regression tests
```

Key documents:

| Document | What it holds |
|---|---|
| `docs/progress_report_zh.md` / `_en.md` | mid-project self-review against the brief |
| `docs/week06_depth_analysis_zh.md` / `_en.md` | the "why it works / when it works" conclusion chain |
| `docs/experiment_evidence_index_zh.md` / `_en.md` | every citable number with its source and caveats |
| `docs/formal_model_zh.md` / `_en.md` | the formal model: sets, parameters, variables, objective, hard vs soft constraints, and what is not modelled |
| `docs/failure_cases_master.md` | 17 failure cases with constraint-level diagnosis |
| `docs/configs_and_parameters.md` | instances, solver settings, seeds, path conventions |
| `docs/v3_ev_collab_note_*`, `docs/week08_*_note_*`, `docs/week07_ablation_std_note_*`, `docs/schneider_evrptw_replication_*` | per-experiment notes |

`src/experiments/` by theme:

| Theme | Scripts |
|---|---|
| Baselines | `week01_baseline`, `week03_experiment`, `week03_reproduce`, `benchmark_*`, `baseline_consolidated`, `baseline_pyvrp_vrptw`, `baseline_ga_vrptw` |
| EVRP-TW core model | `week04_evrp_tw`, `week06_ground_air_evrp_tw` |
| Truck–drone | `week05_truck_drone(_v2)`, `week07_fstsp_repro`, `week07_improvement_ablation` |
| W8 improvements | `week08_lns`, `week08_multidrone`, `week08_multidrone_std`, `drone_scheduling`, `fstsp_instances`, `week08_mc_benchmark`, `fstsp_mc`, `v3_ev_collab` |
| Analysis | `week06_sensitivity`, `week06_multi_objective`, `week06_largeN`, `stat_tests` |
| Schneider replication | `schneider_evrptw`, `schneider_bks_compare` |
| Shared | `sysinfo` (hardware/env reporting) |

---

## Headline results

| Comparison | Result |
|---|---|
| Baselines vs BKS (56 Solomon) | PyVRP −3.0% · OR-Tools +7.2% · my GA +36.6% ± 15.8% |
| V2 (collaborative) vs truck-only EV | 24.8–34.5% lower completion time |
| Ablation | multi-customer sorties +8.6–12.1 pp (main), stop reuse +2.2–4.4 pp |
| LNS vs greedy V2 | +12.5–21.3%, paired Wilcoxon p = 1.7×10⁻¹⁰ |
| Distance from the exact optimum (CP-SAT, small n) | n=8 proven optimal: greedy +31.2%, LNS +16.5% |
| Murray & Chu (2015) replication | V2 10.2–14.2% shorter; c1K1 LNS / published OFV = 0.901 |
| Schneider (2014) replication | distance +50.7% vs BKS, mean vehicles 5.4 vs 2.1 |
| Multi-drone (standard instances) | K=1→5 raises the gain to 46.8–71.4% |
| Drone scheduling | naive rule provably optimal on 64/64 configs |
| V3 (EV + TW + drone) | K=1 −34.7–53.4%, K=3 up to −72.8% vs truck-only EV |

Full numbers and their caveats: `docs/experiment_evidence_index_zh.md`.

---

## Reproduce

```bash
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt

python run_all.py                 # rerun every headline experiment
python -m pytest tests/ -q        # regression tests (about one second)
```

See `REPRODUCE.md` for the conclusion → script → artifact map. Every experiment
prints its machine/environment in the log header and records per-instance
runtime (`runtime_s`) in its CSV.

---

## FURP certificate requirements

To earn the FURP certificate, all three of the following must hold:

1. **Attend > 50%** of programme activities.
2. **Submit a poster** — placed in the repo root as `FURP_Showcase.pdf`.
3. **Present at the Poster Showcase.**

> Research Track — minimum for certification: replicate a cited paper with at
> least **10% innovation**. This repository documents the replication (M&C 2015
> FSTSP) and the added innovation (multi-customer drone sorties + stop reuse,
> LNS, multi-drone, EV+TW integration).

Weekly cadence (progress log in `docs/0-5_weekly.md`, meeting notes in
`docs/meeting_notes/`):

- update the weekly log every week;
- log key takeaways from each meeting;
- attend the weekly meeting.

---

*Bridging the gap between classroom knowledge and cutting-edge research.*
