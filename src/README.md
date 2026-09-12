# `/src` — code, experiments and results

Everything in the project runs from this folder. The repository-level `README.md`
describes the project itself; this file is the map of the code.

```
src/
 ├── experiments/     one script per experiment (theme table in the root README)
 ├── tools/           plotting helpers and the progress-dashboard generator
 ├── instances/       Solomon files, the Schneider E-VRPTW sets, the Murray & Chu FSTSP instances
 ├── results/         run logs; the CSVs are regenerated locally and stay out of git
 ├── data/            small derived inputs
 └── requirements.txt pinned dependencies
```

## How I run it

```bash
# from the repository root, with the project virtual environment active
python -m pytest tests/ -q              # regression tests (about 12 s)
python run_all.py                       # rerun every headline experiment
python src/experiments/week08_lns.py    # or a single experiment
```

Each experiment prints its machine and environment in the log header
(`sysinfo`) and records per-instance runtime (`runtime_s`) in its CSV, so a
rerun on another machine can be compared directly. `REPRODUCE.md` maps every
headline number to the script and artifact behind it.

## Environment

The project runs in an isolated virtual environment with the versions pinned in
`requirements.txt`. `docs/reference/env_record.md` records the exact package
versions, hardware and commands used for the reported runs.
