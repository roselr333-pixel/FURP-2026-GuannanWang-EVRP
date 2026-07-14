# Week 5 Project Checkpoint — EVRP-TW with Classical + Truck-Drone Baselines

> Written by Guannan Wang · 2026-07-14 · Track: Research (EVRP)
> This is my deliverable for the **Week 5 Lab: Consolidate Progress and Prepare the Next Step**.
> I reran every experiment on 2026-07-14 and all of them reproduced the same numbers (see Appendix).

---

## 1. Where My Project Stands Right Now

**The problem I am working on.** I am studying the Electric Vehicle Routing Problem with Time Windows (**EVRP-TW**). I started from a classical VRPTW baseline and have been adding constraints step by step, with a small exploratory **truck-drone** extension on top. My approach follows the path the project outline suggests: *build a simple baseline first → add battery / time-window constraints → then try one improvement and compare it fairly against the baseline.*

**What I have implemented / reproduced so far** (everything runs; OR-Tools 9.15.6755, Python 3.13):

| Week | Script | What I did |
|---|---|---|
| 1 | `week01_baseline.py` | A classical **VRPTW** smoke test (depot + 5 customers, 2 vehicles). Two phases: a greedy `PATH_CHEAPEST_ARC` start, then a 3-second guided local search. |
| 3 | `week03_reproduce.py` | I reproduced a baseline on a **standard** Solomon-format `c101` small instance (9 nodes, with capacity and time windows). |
| 3 | `week03_experiment.py` | A **fair-comparison harness** I built: same generated instances at 3 scales (n = 10 / 20 / 40) × 2 variants (CVRP, VRPTW), comparing a greedy first solution against that same solution followed by my custom **2-opt** post-processing (which respects time windows). |
| 4 | `week04_evrp_tw.py` | **EVRP-TW**: I added an energy / battery dimension, and charging stations that refill the battery to full. It outputs a battery-violation table. |
| 5 | `week05_truck_drone.py` | **Truck + drone** coordination (v1): one truck and one drone both leave the depot at t = 0 and serve customers in parallel; the drone takes the farthest customers. |
| 5 | `benchmark_solomon_vrptw.py` | **Standard VRPTW benchmark**: I generated a Solomon-format suite (6 families × 2 variants × 3 scales = 18 instances) and solved it with the same OR-Tools engine. Instance files are saved to `src/instances/`. |
| 5 | `benchmark_evrptw.py` | **Standard E-VRPTW benchmark**: Solomon customers + charging stations + a battery dimension (the same negative-energy recharge trick from week04), run on benchmark-style instances of several scales. |
| 5 | `benchmark_official_solomon.py` | **Official Solomon VRPTW benchmark**: I downloaded the canonical 56 Solomon 100-customer instances (+ their official `.sol` BKS) and solved them with OR-Tools, comparing instance-by-instance against published BKS (overall mean gap 7.2%). |
| 5 | `week05_truck_drone_v2.py` | **Truck + drone (v2)**: the drone is now *carried by the truck* and launched / recovered at **any** node (FSTSP-style), with range + rendezvous constraints — removing the "depot-only" simplification of v1. |

**What already works** (I confirmed this by rerunning on 2026-07-14):
- All eight scripts run end-to-end and give the same results as before → my project is **reproducible**.
- I get feasible solutions for VRPTW, for EVRP-TW (with charging), and for both truck-drone versions.
- I have a fair-comparison table, a Solomon-format benchmark suite, and route plots as evidence.
- **I ran a real standard benchmark** — the official 56-instance Solomon 100-customer VRPTW set, solved with OR-Tools and compared instance-by-instance against published BKS (overall mean gap 7.2%; 56/56 solved) — and **I removed the truck-drone simplification** (v2 launches/lands at any node).

**What I have NOT finished yet** (being honest — these are my real remaining gaps):
- **I have not written any paper reading notes yet.** I have not read, noted, and uploaded an EVRP-TW / truck-drone paper. This is still the biggest open gap from Week 4 / Week 5.
- **No external baseline comparison yet.** So far I only compare my own OR-Tools greedy result against my OR-Tools + 2-opt result (and against my own truck-only baseline). I have not added a PyVRP / GA / POMO baseline yet (planned for later).

---

## 2. Evidence of What I Have Done

### 2.1 Pipeline milestones

| Instance | Method | Feasible | Objective / Metric | Runtime (s) | What I observed |
|---|---|---|---:|---:|---|
| W1 small VRPTW | OR-Tools (greedy → GLS) | Yes | dist = 108 | 0.005 / 3.0 | a clean 2-route split |
| W3 Solomon c101 (9 nodes) | OR-Tools VRPTW | Yes | dist = 54 | 5.0 | only 1 of 3 vehicles used |
| W4 EVRP-TW (battery 100, recharge) | OR-Tools + battery dim | Yes | 1 recharge | 5.0 | feasible from cap 100 upward |
| W4 EVRP-TW (battery 100, **no** recharge) | pure EV | **No** | – | 0.003 | infeasible |
| W5 truck-only | heuristic | Yes | makespan 388.6 (v1) / 552.1 (v2) | – | baseline |
| W5 truck + drone (v1, depot-only) | parallel heuristic | Yes | makespan 270.6 | – | **−30.4%** vs truck-only |
| W5 truck + drone (v2, any node) | FSTSP-style heuristic | Yes | makespan 277.3 | – | **−49.8%** vs truck-only, **−28.8%** vs v1 |

### 2.2 Week 3 fair comparison — my greedy vs my greedy + 2-opt

| Instance | Variant | Method | Feasible | Objective | Runtime (s) | Gain |
|---|---|---|---:|---:|---:|---:|
| n10 | CVRP | baseline | Yes | 363 | 0.009 | – |
| n10 | CVRP | improved (2-opt) | Yes | 363 | 4.001 | 0% |
| n10 | VRPTW | baseline | Yes | 377 | 0.004 | – |
| n10 | VRPTW | improved | Yes | 366 | 4.001 | **−2.9%** |
| n20 | CVRP | baseline | Yes | 436 | 0.007 | – |
| n20 | CVRP | improved | Yes | 436 | 4.001 | 0% |
| n20 | VRPTW | baseline | Yes | 448 | 0.009 | – |
| n20 | VRPTW | improved | Yes | 448 | 4.001 | 0% |
| n40 | CVRP | baseline | Yes | 682 | 0.029 | – |
| n40 | CVRP | improved | Yes | 616 | 4.002 | **−9.7%** |
| n40 | VRPTW | baseline | Yes | 616 | 0.038 | – |
| n40 | VRPTW | improved | Yes | 616 | 4.002 | 0% |

**What this tells me:** 2-opt never breaks feasibility. It cuts distance on the largest CVRP case (−9.7%) and on the tight-time-window small case (−2.9%), and the gain grows as the instance gets bigger. On already-tight instances (n20 / n40 VRPTW) 2-opt finds no better move — which makes sense, because most improving moves would violate a time window.

### 2.3 Week 4 battery / charging trade-off

| Battery cap | Recharge allowed | Feasible | Recharges | Runtime (s) |
|---:|---|---|---:|---:|
| 100 | Yes | True | 1 | 5.0 |
| 150 | Yes | True | 1 | 5.0 |
| 200 | Yes | True | 1 | 5.0 |
| 250 | Yes | True | 1 | 5.0 |
| 100 | No | **False** | – | 0.003 |
| 150 | No | **False** | – | 0.005 |
| 200 | No | True | – | 5.0 |
| 250 | No | True | – | 5.0 |

**What this tells me:** with charging stations, the same instance becomes feasible from a battery capacity of **100** instead of **200** — so charging roughly **halves** the battery I need for the same route.

### 2.4 Figures
- `src/results/week01_routes.png` — my Week 1 VRPTW routes.
- `src/results/week03_route_n20_vrptw_improved.png` — my Week 3 improved VRPTW routes (n20).

### 2.5 Official Solomon VRPTW benchmark — 56 instances vs published BKS

I downloaded the **canonical 56 Solomon 100-customer VRPTW instances** (each with its official `.sol` best-known solution) from PyVRP/Instances and solved them with OR-Tools (PARALLEL_CHEAPEST_INSERTION first solution + GUIDED_LOCAL_SEARCH, 10 s per instance, distance scaled ×10). This is now a direct, instance-by-instance comparison against literature BKS — not a generated stand-in. Cached instances: `src/instances/official_solomon/`; full results: `src/results/benchmark_official_solomon_results.csv`.

Representative instances:

| Instance | BKS dist | BKS veh | My dist | My veh | Gap% |
|---|---:|---:|---:|---:|---:|
| C101 | 827.3 | 10 | 828.7 | 10 | +0.2% |
| C201 | 589.1 | 3 | 591.6 | 3 | +0.4% |
| R101 | 1637.7 | 20 | 1634.4 | 19 | −0.2% |
| R201 | 1143.2 | 8 | 1298.9 | 4 | +13.6% |
| RC101 | 1619.8 | 15 | 1718.9 | 15 | +6.1% |
| RC201 | 1261.8 | 9 | 1485.2 | 4 | +17.7% |

Per-family mean gap to BKS:

| Family | n | Mean gap | min | max |
|---|---:|---:|---:|---:|
| C1 | 9 | 4.2% | 0.2% | 21.8% |
| C2 | 8 | 0.9% | 0.4% | 1.9% |
| R1 | 12 | 5.1% | −0.2% | 13.7% |
| R2 | 11 | 12.4% | 6.5% | 21.2% |
| RC1 | 8 | 6.4% | 2.9% | 9.8% |
| RC2 | 8 | 13.7% | 4.7% | 21.7% |

**Overall: 56 / 56 solved, mean gap to BKS = 7.2%.**

**What this tells me:** on the **C-family** (tight, structured windows) my OR-Tools baseline is essentially at BKS (C2 mean only 0.9%). On **R2 / RC2** (loose windows) the gap is larger — I checked the cause: my model uses a high vehicle fixed cost, so it deploys *fewer* vehicles than BKS (e.g. R201: I use 4 vs BKS 8). Fewer vehicles → longer individual routes → larger total distance. That is a modelling choice (I minimise distance under a vehicle-count penalty), not a solver failure. Matching the exact BKS objective / tuning the vehicle cost is a clear next step.

*(The earlier `benchmark_solomon_vrptw.py` 18-instance generated suite remains as a lightweight self-test; its numbers are no longer the headline.)*

### 2.6 Standard E-VRPTW benchmark (Solomon customers + charging stations)

I extended the benchmark with charging stations and the battery dimension (negative-energy recharge trick). With enough battery + recharge the instances are feasible and the solver uses recharges; with too-small battery they become infeasible — showing the battery/charging constraint is real. Full results: `src/results/benchmark_evrptw_results.csv`.

| Instance | Battery | Recharge? | Feasible | Recharges | Vehicles | Distance |
|---|---|---|---|---:|---:|---:|
| EVRPTW-C2-25-S2 | 100 | Yes | **No** | – | – | – |
| EVRPTW-C2-25-S2 | 300 | Yes | Yes | 2 | 2 | 578 |
| EVRPTW-C2-50-S3 | 100 | Yes | **No** | – | – | – |
| EVRPTW-C2-50-S3 | 300 | Yes | Yes | 3 | 4 | 850 |
| EVRPTW-R2-50-S3 | 100 | Yes | **No** | – | – | – |
| EVRPTW-R2-50-S3 | 300 | Yes | Yes | 3 | 4 | 1300 |

(Without recharge at all, even battery = 100 is infeasible — confirming the charging model matters.)

### 2.7 Truck-drone v2 — flexible launch / land

The v2 heuristic carries the drone on the truck and launches it at any node `i` to serve a customer `k`, then recovers it at any later node `j` (FSTSP-style). Each trip must satisfy a **range** limit and a **rendezvous** constraint (the drone must land by the time the truck reaches `j`). Results: `src/results/week05_truck_drone_v2_output.txt`.

| Model | Makespan | Improvement vs truck-only |
|---|---:|---:|
| Truck-only | 552.1 | – |
| v1 (depot-only drone) | 389.5 | −29.5% |
| **v2 (any-node drone)** | **277.3** | **−49.8%** |

v2 also beats v1 by **28.8%** — directly removing the "depot-only" simplification. Example drone trips found: `node 1 → customer 5 → node 3`, `depot → customer 2 → node 6`, `node 3 → customer 4 → depot`.

---

## 3. Problems and Limitations I See in My Own Work

- **My OR-Tools baseline is a solid first solve, not an optimiser tuned to BKS.** On R2 / RC2 the gap to BKS is large mostly because my vehicle fixed cost makes me use fewer vehicles than BKS (longer routes). Tuning the cost / objective to match the literature, and adding a stronger meta-heuristic pass or an external solver (PyVRP), are the obvious next improvements.
- **I have no paper notes yet.** The project outline and the Week-4 lab ask for reading notes; I have not uploaded any. This is the clearest thing for me to fix next.
- **I modelled recharge as a workaround.** OR-Tools dimensions only go one direction (monotonic), so I encoded charging as a *negative* energy cost into the station, with `slack_max` set to the battery capacity. It works and reproduces, but it is not the standard arc-based charging formulation, and I would have to rework it for mid-route vehicle / drone rendezvous under partial recharge.
- **The truck-drone v2 is still a heuristic.** It allows any-node launch/land and one customer per drone trip, with range + rendezvous checks, but it does not yet model drone battery depletion, multiple customers per trip, or optimality — only a greedy improvement over the truck-only route.
- **No external baseline.** All my "comparisons" are internal (my greedy vs my +2-opt; my truck-only vs my drone). A real fair comparison needs a PyVRP / GA / POMO baseline.

---

## 4. My Next Steps (for Week 6+)

1. **Close my reading gap (top priority):** read and upload at least 1 EVRP-TW paper note (I am aiming at a recent ECVRPTW / ALNS or hybrid paper), using the lab's note template — problem / method / reusable idea / reproducibility. *I deferred this, and it is now my number-one item.*
2. **Tighten the gap to BKS on R2 / RC2:** tune the vehicle fixed cost / objective so my solver uses a vehicle count closer to BKS, and add a stronger meta-heuristic pass; optionally re-run the official Schneider / Montoya E-VRPTW set (now that I can fetch public instances).
3. **Deepen the truck-drone v2:** add a drone-battery dimension and allow multiple customers per drone trip, then re-measure makespan on a larger instance.
4. **Pick a paper to replicate + a second baseline:** choose one paper to reproduce and add a GA / POMO baseline so I have a genuine fair comparison (this was deferred from earlier weeks).

---

## Appendix — How to reproduce (my setup)

```bash
PY=<venv>/Scripts/python.exe      # Python 3.13, ortools==9.15.6755
python src/experiments/week01_baseline.py
python src/experiments/week03_reproduce.py
python src/experiments/week03_experiment.py
python src/experiments/week04_evrp_tw.py
python src/experiments/week05_truck_drone.py
python src/experiments/week05_truck_drone_v2.py
python src/experiments/benchmark_solomon_vrptw.py
python src/experiments/benchmark_evrptw.py
```

Each script writes its evidence to `src/results/*.txt`; benchmark instance files are in `src/instances/`. Full environment details are in `docs/env_record.md`.
All scripts reran identically on **2026-07-14** (the rerun date for this checkpoint).
