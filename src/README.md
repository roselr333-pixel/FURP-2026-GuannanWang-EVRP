# `/src` — your work goes here

Put all your code, scripts, notebooks, experiment configs, and project materials in this folder.

**Research Track reminder:** your project should reproduce a cited paper and add **at least 10% innovation** (something new on top of the replication). Organise this folder however suits your project, but keep it tidy enough that a reviewer can follow what you did.

## Layout

```
/src
 ├── README.md                 ← this file
 ├── requirements.txt          ← exact pinned dependencies (reproducibility)
 ├── data/                     ← datasets (or links if too large to commit)
 ├── experiments/
 │    └── week01_baseline.py   ← Week 1 OR-Tools VRPTW smoke test
 └── results/
      └── week01_baseline_output.txt  ← solver output evidence
```

## Environment setup (reproducible)

This project uses an **isolated virtual environment** so it never pollutes your system Python.

```bash
# 1. Create the venv (use your Python 3.13 interpreter)
python -m venv venv
# Windows:
venv\Scripts\activate

# 2. Install pinned dependencies
pip install -r src/requirements.txt
```

> Pinned version used for the Week 1 baseline: `ortools==9.15.6755` on Python 3.13 (Windows).

## How to run the Week 1 baseline

```bash
# From the repository root:
python src/experiments/week01_baseline.py
```

Expected output (small VRPTW, 1 depot + 5 customers, 2 vehicles):

```
STATUS: FEASIBLE
PHASE A — greedy first solution (PATH_CHEAPEST_ARC)
  Objective (total distance): 108
  Runtime: 0.0052 s
PHASE B — guided local search (3 s budget)
  Objective (total distance): 108
  Runtime: 3.0002 s
```

The script also writes full output to `src/results/week01_baseline_output.txt`.

## What comes next

- **Week 3:** reproduce this baseline on a *standard* benchmark (e.g. a Solomon VRPTW instance or a PyVRP CVRP instance) and log objective / feasibility / runtime.
- **Week 4:** add battery capacity + charging stations → turn the VRPTW into **EVRP-TW**.
- **Week 5+:** model truck-drone synchronization, then a learning/hybrid method, then improvement + ablation.
