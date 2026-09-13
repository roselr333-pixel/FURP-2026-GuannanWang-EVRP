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
docs/                  reference / analysis / weekly / baselines (index in docs/README.md)
src/experiments/       all experiment code
src/tools/             plotting / dashboard helpers
src/results/           run logs (CSV outputs are regenerated locally)
figures/               figures used in the reports
tests/                 pytest regression tests
```

Key documents:

| Document | What it holds |
|---|---|
| `docs/analysis/progress_report_zh.md` / `_en.md` | mid-project self-review against the brief |
| `docs/analysis/week06_depth_analysis_zh.md` / `_en.md` | the "why it works / when it works" conclusion chain |
| `docs/reference/experiment_evidence_index_zh.md` / `_en.md` | every citable number with its source and caveats |
| `docs/reference/formal_model_zh.md` / `_en.md` | the formal model: sets, parameters, variables, objective, hard vs soft constraints, and what is not modelled |
| `docs/reference/failure_cases_master.md` | 13 failure cases with constraint-level diagnosis |
| `docs/reference/configs_and_parameters.md` | instances, solver settings, seeds, path conventions |
| `docs/weekly/*` | weekly notes and per-experiment notes (week 1-8, plus V3) |
| `docs/baselines/*` | GA baseline report and the Schneider (2014) replication |
| `docs/README.md` | the full document index |

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
| Murray & Chu (2015) replication | V2 10.2–14.2% shorter; c1K1 LNS / published OFV = 0.924 |
| Schneider (2014) replication | distance +50.7% vs BKS, mean vehicles 5.4 vs 2.1 |
| Multi-drone (standard instances) | K=1→5 raises the gain to 46.8–71.4% |
| Drone scheduling | naive rule provably optimal on 64/64 configs |
| V3 (EV + TW + drone) | vs truck-only EV: K=1 33.5–52.4% shorter, K=3 up to 72.5% |

Full numbers and their caveats: `docs/reference/experiment_evidence_index_zh.md`.

---

## Five-minute tour

If you only have five minutes, read these four things in this order:

1. **`figures/baseline_consolidated.png`** — the three baselines on the *same* 56
   official Solomon instances: PyVRP −3.0%, OR-Tools +7.2%, my GA +36.6%. (OR-Tools
   is a 10 s time-budgeted search: 7.2–8.1% across runs; PyVRP is seeded and stable.)
2. **`figures/v3_ablation.png`** — what actually buys the collaborative gain:
   multi-customer sorties, not extra take-offs or extra truck stops. At N=20 the
   multi-customer term even turns slightly negative, which is the honest boundary
   of the idea.
3. **`figures/lns_vs_greedy.png` + `figures/multidrone_std.png`** — the improvement
   phase (+12.5–21.3% over the greedy) and the drone-count sweep, including the
   scheduling certificate (the naive rule is provably optimal on 64/64 configs).
4. **`docs/reference/failure_cases_master.md`** — the 13 diagnosed failure cases
   (which instance, which constraint failed, what I would change next). This is the
   boundary section of the project.

### Which figure answers which question

Every figure below is a step in `run_all.py`; the figure tools run last, after the
experiments that produce their CSVs. Numbers, sources and caveats for all of them:
`docs/reference/experiment_evidence_index_en.md`.

| Figure | Question it answers | Headline number | Produced by |
|---|---|---|---|
| `figures/baseline_consolidated.png` | How do the three baselines compare with the published BKS on the same instances? | PyVRP −3.0% · OR-Tools +7.2% (7.2–8.1% across runs) · my GA +36.6% ± 15.8% | `baseline_consolidated.py` |
| `figures/pyvrp_family_gap.png` | Is PyVRP below BKS on every family? | yes — all six family means are negative | `baseline_pyvrp_vrptw.py` |
| `figures/sensitivity_panels.png` | Which design variable moves the gain most? | battery Q 120→500: 41.2%→29.7%; range R 60→160: 15.4%→34.4% (then flat); customers/sortie 1→3: 20.5%→37.1% | `week06_sensitivity.py` |
| `figures/mo_scatter.png`, `figures/mo_tradeoff.png` | Is there a distance / completion-time trade-off? | the weighted sum reaches −32% distance and −34% makespan | `week06_multi_objective.py` |
| `figures/largen_scale_decay.png` | At what size does collaboration stop paying? | V2 vs V1: 8.6% (N=30) → 3.4% (N=50) → 0.5% (N=100) | `src/tools/gen_largen_figure.py` |
| `figures/ablation_std.png` | Does the ablation survive on official Solomon topologies? | multi-customer +7.2–8.9 pp (synthetic set: +8.6–12.1 pp) — same main driver | `src/tools/gen_ablation_std_figure.py` |
| `figures/v3_ablation.png` | Which factor drives the gain under EV + time windows? | multi-customer +8.5–12.5 pp, stop reuse +1.9–5.3 pp; extra take-offs not significant (p=0.139) | `src/tools/gen_v3_ablation_figure.py` |
| `figures/drone_energy.png` | What changes once the drone has a payload-aware energy budget? | multi-customer gain +10.4→+6.1 pp (synthetic) and +6.6→+5.4 pp (standard); the published heuristic's plans are only 42%/48% energy-feasible at β=0.04, mine 100% | `src/tools/gen_drone_energy_figure.py` |
| `figures/lns_vs_greedy.png` | Does the improvement phase pay off? | +12.5–21.3% over the greedy (paired Wilcoxon p=1.7×10⁻¹⁰) | `src/tools/plot_lns.py` |
| `figures/multidrone.png` | How much do extra drones help (synthetic instances)? | N=50: 29.5% (K=1) → 38.1% (K=3) | `src/tools/plot_multidrone.py` |
| `figures/multidrone_std.png` | Same question on standard instances, plus the scheduler | K=1→5 raises the gain to 46.8–71.4%; naive scheduler optimal on 64/64 configs | `src/tools/plot_multidrone_std.py` |
| `figures/exact_gap.png` | How far is the heuristic from the exact optimum? | n=8 (proven optimal): greedy +31.2%, LNS +16.5% | `src/tools/plot_exact_gap.py` |
| `figures/schneider_routes.png`, `figures/schneider_vehcomp.png` | How close is my EVRP-TW to Schneider (2014)? | 18/18 fully served, distance +50.7%, 5.4 vs 2.1 vehicles (multi-trip is why) | `src/tools/plot_schneider_routes.py` |
| `src/results/week01_routes.png` | Week-1 smoke test | 5-customer VRPTW, both phases feasible | `week01_baseline.py` |
| `src/results/week03_route_n20_vrptw_improved.png` | Week-3 fair comparison | 2-opt: 682→616 (−9.7%) at n=40 | `week03_experiment.py` |

---

## Reproduce

```bash
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt

python run_all.py                 # rerun every experiment and every figure
python -m pytest tests/ -q        # 95 regression tests, about 15 s
```

See `REPRODUCE.md` for the conclusion → script → artifact map. The experiment
scripts print their machine/environment in the log header and record per-instance
runtime (`runtime_s`) in their CSV; the baseline scripts report wall-clock time in
their logs instead.

To regenerate one specific figure without rerunning everything, run its script
directly, e.g. `python src/tools/plot_lns.py` (it reads the CSV the corresponding
experiment produced).

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

Weekly cadence (progress log in `docs/weekly/0-5_weekly.md`, meeting notes in
`docs/meeting_notes/`):

- update the weekly log every week;
- log key takeaways from each meeting;
- attend the weekly meeting.

---

*Bridging the gap between classroom knowledge and cutting-edge research.*
