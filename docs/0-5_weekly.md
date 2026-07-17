# Weekly Progress Log

> Update this file **every week**. Add a new entry at the top for each week.
> This is the first thing we check during review. Keep it honest and specific — it also feeds your attendance record (Rule 1).

**How to use:** copy the *Week template* block below for each new week. Newest week goes at the top.

---

## Important note 

Weeks 1–5 were **consolidated during a catch-up sprint on 2026-07-07** (two sessions).
Earlier meetings (Weeks 2–4) were missed due to **family circumstances**; the
leave emails have **already been sent** (confirmed). Week 5 meeting was attended.

**Deferred items (per current plan — not started yet):** paper reading notes
( will add after reading the papers), choosing the paper to replicate
(planned for 2026-07-08/09), and POMO / GA baselines (to be attempted at a later
stage). These are honestly marked as future work below.

### Lab-deliverable status (honest)
| Lab | Required | Status after catch-up |
|---|---|---|
| W1 | smoke test + env record + reflection + plot | ✅ baseline, env record, route PNG, reflection |
| W2 | recreate a baseline + compare at ≥2 scales | 🟡 OR-Tools baseline recreated & compared at 3 scales (10/20/40); POMO/GA recreation = future work |
| W3 | fair comparison, ≥3 scales, summary table, report, failure cases | ✅ full harness + report + 3 failure cases |
| W4 | ≥1 paper note + ≥1 new experiment + method improvement | 🟡 EVRP-TW experiment + 2-opt improvement done; paper notes **deferred** (to be added after reading, planned 2026-07-08/09) |
| W5 | truck-drone formulation + sync note | ✅ heuristic baseline (depot-only launch) |

---

## Week template — copy me

### Week N — YYYY-MM-DD

**Attended this week's meeting:** Yes / No (if No, did you email leave? Yes / No)

**Progress this week**
- _What did you actually do / finish?_

**Challenges & blockers**
- _What got in the way? What are you stuck on?_

**Next steps**
- _What will you do next week?_

**Hours spent (optional):** _e.g. 6h_

**Links (optional):** _commits, notebooks, docs, datasets..._

---

<!-- =================  YOUR ENTRIES BELOW  ================= -->

### Week 5 — 2026-07-07 (catch-up sprint) + 2026-07-14 (benchmark & truck-drone v2 added)

**Attended this week's meeting:** Yes

**Progress this week**
- Implemented a **truck + drone collaborative routing** heuristic baseline (`src/experiments/week05_truck_drone.py`): truck and drone start at depot at t=0, work in parallel; drone takes the farthest customers. makespan: truck-only 388.6 → truck+drone 270.6 (**−30.4%**).
- *Added 2026-07-14 (supports the Week-5 checkpoint):* ran a **standard VRPTW benchmark** — generated a Solomon-format suite (6 families × 2 variants × 3 scales = 18 instances) and solved it with OR-Tools (`src/experiments/benchmark_solomon_vrptw.py`); also ran a **standard E-VRPTW benchmark** with charging stations + battery (`src/experiments/benchmark_evrptw.py`).
- *Added 2026-07-14:* upgraded the truck-drone model to **v2** (`src/experiments/week05_truck_drone_v2.py`) — the drone is now carried by the truck and launched/recovered at **any** node (FSTSP-style) with range + rendezvous constraints. makespan drops further to **277.3 (−49.8% vs truck-only, −28.8% vs v1)**.
- *Added 2026-07-14 (later):* ran the **official Solomon 56-instance VRPTW set** (downloaded with their published `.sol` BKS from PyVRP/Instances) and solved with OR-Tools — **56/56 feasible, mean gap to BKS = 7.2%** (`src/experiments/benchmark_official_solomon.py`, `src/results/benchmark_official_solomon_results.csv`, instances in `src/instances/official_solomon/`). This now serves as the main benchmark (in place of the earlier generated suite).
- Outputs: `src/results/week05_truck_drone_output.txt`, `src/results/benchmark_vrptw_results.csv`, `src/results/benchmark_evrptw_results.csv`, `src/results/week05_truck_drone_v2_output.txt`, `src/results/benchmark_official_solomon_results.csv`; instance files in `src/instances/` and `src/instances/official_solomon/`.
- *The foundational truck-drone paper (Murray & Chu 2015, FSTSP) has **not** been read/note-taken yet — paper notes are deferred (planned 2026-07-08/09).*

**Challenges & blockers**
- Official Solomon VRPTW benchmark now run (56/56 solved, mean gap to BKS 7.2%); the larger gap on R2/RC2 is from my vehicle fixed-cost choice (fewer vehicles than BKS), to be tuned next.
- Truck-drone v2 is a greedy heuristic (one customer per trip, no drone battery modelled yet).

**Next steps**
- Tune the vehicle fixed cost / objective so my solver uses a vehicle count closer to BKS (especially R2/RC2), and re-run the official Schneider / Montoya E-VRPTW set; optionally add a PyVRP baseline for a genuine external comparison.
- After reading the truck-drone literature, add a drone-battery dimension and allow multiple customers per trip.

**Hours spent (optional):** 5h (catch-up) + ~3h (2026-07-14)

**Links (optional):** `src/experiments/week05_truck_drone.py`, `src/experiments/week05_truck_drone_v2.py`, `src/experiments/benchmark_solomon_vrptw.py`, `src/experiments/benchmark_evrptw.py`, `src/results/week05_truck_drone_output.txt`, `src/results/week05_truck_drone_v2_output.txt`, `src/results/benchmark_vrptw_results.csv`, `src/results/benchmark_evrptw_results.csv`, `docs/week05_checkpoint.md` (Week 5 checkpoint), `docs/week05_checkpoint_zh.md` (中文)

---

### Week 4 — 2026-07-07 (completed in catch-up sprint)

**Attended this week's meeting:** No (family circumstances — leave emailed: Yes)

**Progress this week**
- Extended the classical VRPTW into **EVRP-TW** by adding a battery dimension + charging stations (`src/experiments/week04_evrp_tw.py`).
- Battery = energy used; travelling consumes energy; arriving at a charging station recharges to full. Battery must never exceed capacity.
- Produced the **battery violation table** (key Week 4 deliverable):
  - with recharge: feasible from battery capacity **100** upward (1 recharge used);
  - without recharge: feasible only from capacity **200** upward.
  - ⇒ adding charging stations halves the required battery for the same instance.
- Output: `src/results/week04_evrp_tw_output.txt`.
- **Documented method improvement**: the Week-3 2-opt post-processing is a "small meaningful improvement" the lab explicitly values (added local-search on top of the OR-Tools first solution).
- *Paper reading notes (Week 4 minimum = ≥1) are **deferred** — the student will add them after reading the papers (planned 2026-07-08/09).*

**Challenges & blockers**
- OR-Tools dimensions are monotonic, so "recharge" had to be modelled via a *negative* energy transit into charging stations, with `slack_max` set to the battery capacity. Took debugging to get right.

**Next steps**
- Add the EVRP-TW variant into the Week-3 fair-comparison harness (same instances/scales) so battery + charging are compared head-to-head with CVRP/VRPTW.
- Choose the paper to replicate (planned 2026-07-08/09) and, after reading, add the paper notes.

**Hours spent (optional):** 15h (plus shared catch-up time)

**Links (optional):** `src/experiments/week04_evrp_tw.py`, `src/results/week04_evrp_tw_output.txt`

---

### Week 3 — 2026-07-07 (completed in catch-up sprint)

**Attended this week's meeting:** No (family circumstances — leave emailed: Yes)

**Progress this week — the core gap from before is now addressed**
- Built a **fair-comparison experiment harness** (`src/experiments/week03_experiment.py`) that satisfies the Week-3 lab and the benchmark minimum standard:
  - **Same instance data** reused across variants (fair comparison).
  - **3 sizes**: 10 / 20 / 40 customers (small / medium).
  - **Variants**: CVRP (capacity) and VRPTW (capacity + time windows).
  - **Method axis (baseline vs improved)**: greedy first solution vs first solution + custom **2-opt** post-processing (respects time windows).
  - Per run records: instance, size, method, variant, feasibility, objective, runtime, #vehicles, TW violations, seed.
- Produced:
  - a **cleaned summary table** (lab format): `src/results/week03_summary_table.csv`
  - a **raw log + aggregated table + failure cases**: `src/results/week03_experiment_log.txt`
  - a **short report** (Setup / Results / Discussion / Conclusion + failure analysis): `docs/week03_report.md`
  - a **route plot** (PNG): `src/results/week03_route_n20_vrptw_improved.png`
- **Key result:** 2-opt improvement is never worse and cuts distance up to **−9.7% at n40-CVRP (682→616)** and **−2.9% at n10-VRPTW (377→366)**; both methods 100% feasible; gain grows with size.
- **3 failure cases** with constraint-level diagnosis (capacity / time-window / energy) — meets the benchmark "≥3 failure cases" rule.

**Challenges & blockers**
- Instance generation must keep the *same* data across variants for fairness; a 2-opt that ignored time windows would break VRPTW feasibility, so the post-processing checks TW before accepting a move.

**Next steps**
- Test the 100+ "large" tier; add EVRP-TW and truck-drone variants into this harness; compare against an external baseline (PyVRP, or a GA/POMO baseline — POMO/GA are deferred to a later stage per the current plan).

**Hours spent (optional):** 15h (plus shared catch-up time)

**Links (optional):** `src/experiments/week03_experiment.py`, `src/results/week03_summary_table.csv`, `src/results/week03_experiment_log.txt`, `docs/week03_report.md`, `src/results/week03_route_n20_vrptw_improved.png`

---

### Week 2 — 2026-06-22 (retrospective updated 2026-07-07)

**Attended this week's meeting:** No (family circumstances — leave emailed: Yes)

**Progress this week**
- Studied Python and part of the machine-learning / RL background (programming foundation was weak at the start).
- Looked at POMO but did **not** finish; only did basic learning.
- *Retrospective (2026-07-07):* POMO was the wrong entry point. The project Lab reserves POMO/RL for students who already understand CVRP + neural training. Switched to the OR-Tools **classical VRPTW** path, which is now the foundation for Weeks 1–5.
- *Lab deliverable status:* the Lab lists **OR-Tools as a valid starter path** (Step 1, option 1). We recreated the OR-Tools baseline and, in Week 3, compared it across **3 scales (10/20/40)** with a results table — this partially satisfies the Week-2 "recreate a baseline + compare at ≥2 scales" requirement **for the OR-Tools track**.

**Challenges & blockers**
- Paper reading took a long time; many concepts were unfamiliar.
- Spent time on POMO/ML without ever running a solver — this is what caused the slide in progress.

**Next steps (still open — honest)**
- The Lab suggests also recreating a **GA** (py-ga-VRPTW) or **POMO** baseline and comparing methodologies. This is **deferred to a later stage** per the current plan; the current comparison is OR-Tools greedy vs OR-Tools + 2-opt.

**Hours spent (optional):** 30h

---

### Week 1 — 2026-06-13 (baseline actually completed 2026-07-07)

**Attended this week's meeting:** Yes

**Progress this week**
- Set up the repository from the FURP template.
- *The Week 1 baseline smoke test (required deliverable) was actually completed on 2026-07-07 during the catch-up sprint* — see `docs/week01_checkpoint.md`.
- Baseline: small VRPTW (1 depot + 5 customers, 2 vehicles) solved with OR-Tools → **FEASIBLE**, objective (total distance) = **108**, runtime 0.005 s (greedy) / 3.0 s (local search). Code: `src/experiments/week01_baseline.py`; output: `src/results/week01_baseline_output.txt`.
- Added a **route plot** (PNG): `src/results/week01_routes.png`.
- Added a standalone **Environment Record**: `docs/env_record.md` (OS, Python, package manager, ortools version, exact install/run commands, hardware, solver params).

**Next steps**
- Move to literature + data formats (Week 2) and baseline reproduction on a standard instance (Week 3) — both done in the catch-up sprint.

**Hours spent (optional):** 10h (setup) + 3h (baseline + plot + env record, 2026-07-07)
