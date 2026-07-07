# Week 1 Checkpoint

> Filled during a catch-up sprint on 2026-07-07. The original Week 1 was 2026-06-13
> (repo setup only); the actual baseline smoke test is completed here.

## Team info

- Team name: Guannan Wang (individual)
- Members: Guannan Wang
- Date: 2026-07-07 (baseline completed)

## Environment

- [x] Environment created
      - Isolated venv: `C:\Users\admin\.workbuddy\binaries\python\envs\furp`
      - Python 3.13.14 (managed)
      - Full record: `docs/env_record.md` (OS, Python, package manager, solver version, exact install/run commands, hardware, solver params)
- [x] Dependencies installed
      - `ortools==9.15.6755` (installed via `pip install ortools`)
      - `numpy`, `pandas`, `matplotlib` (for data + route plots)
      - pinned in `src/requirements.txt`
- [x] Repo structure understood
      - `/docs` (weekly logs, meeting notes), `/src` (code), root `README.md`

## Baseline run

- [x] Baseline command executed
      - `python src/experiments/week01_baseline.py`
- [x] Objective value reported
      - **108** (total distance), for both Phase A (greedy) and Phase B (local search)
- [x] Feasibility status reported
      - **FEASIBLE** — capacity (<=20/vehicle) and time windows both satisfied
- [x] Evidence attached
      - `src/results/week01_baseline_output.txt`
      - `src/results/week01_routes.png` (route plot — one plot/route text per Week 1 Lab deliverable)

## Reflection

1. **Main setup issue:** getting a clean Python environment without polluting the
   system interpreter, and figuring out the correct OR-Tools API calls
   (`solution.ObjectiveValue()`, `AddDimension`, time windows via `CumulVar`).
2. **How it was solved:** created an isolated `venv` with the managed Python 3.13
   and installed OR-Tools via pip; started from the official OR-Tools VRPTW example
   and shrank it to a 6-node instance.
3. **Current risk for Week 2:** in previous weeks I spent time on Python/ML basics
   and POMO without ever running a solver. The fix is to stay on the OR-Tools
   *classical* path and only add battery / drone constraints **after** the baseline
   is reproduced on a standard benchmark (Week 3). Do **not** jump to POMO or
   truck-drone yet.
