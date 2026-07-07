# Weekly Progress Log

> Update this file **every week**. Add a new entry at the top for each week.
> This is the first thing we check during review. Keep it honest and specific — it also feeds your attendance record (Rule 1).

**How to use:** copy the *Week template* block below for each new week. Newest week goes at the top.

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

### Week 5 — 2026-07-07 (completed in catch-up sprint)

**Attended this week's meeting:** Yes

**Progress this week**
- Implemented a **truck + drone collaborative routing** heuristic baseline (`src/experiments/week05_truck_drone.py`).
- One truck and one drone start at the depot at t=0 (synchronization) and work in parallel; each customer is assigned to truck or drone (drone takes the farthest customers).
- Reported **makespan**: truck-only = 388.6; truck+drone = 270.6 → **30.4% shorter makespan**.
- Output: `src/results/week05_truck_drone_output.txt`.

**Challenges & blockers**
- Truck-drone synchronization (mid-route launch/recovery, drone battery) is simplified; current baseline launches/recovers the drone only at the depot.

**Next steps**
- Extend the model with mid-route rendezvous and a drone battery constraint; compare against the OR-Tools classical baseline.

**Hours spent (optional):10h (plus shared catch-up time)

**Links (optional):** `src/experiments/week05_truck_drone.py`, `src/results/week05_truck_drone_output.txt`

---

### Week 4 — 2026-07-07 (completed in catch-up sprint)

**Attended this week's meeting:** No (family circumstances — leave to be emailed)

**Progress this week**
- Extended the classical VRPTW into **EVRP-TW** by adding a battery dimension + charging stations (`src/experiments/week04_evrp_tw.py`).
- Battery = energy used; travelling consumes energy; arriving at a charging station recharges to full. Battery must never exceed capacity.
- Produced the **battery violation table** (key Week 4 deliverable):
  - with recharge: feasible from battery capacity **100** upward (1 recharge used);
  - without recharge: feasible only from capacity **200** upward.
  - ⇒ adding charging stations halves the required battery for the same instance.
- Output: `src/results/week04_evrp_tw_output.txt`.

**Challenges & blockers**
- OR-Tools dimensions are monotonic, so "recharge" had to be modelled via a *negative* energy transit into charging stations, with `slack_max` set to the battery capacity. Took debugging to get right.

**Next steps**
- Add the battery/EVRP-TW constraint on top of the standard benchmark (Week 3 instance); record time-window AND battery violations together.

**Hours spent (optional):** 15h (plus shared catch-up time)

**Links (optional):** `src/experiments/week04_evrp_tw.py`, `src/results/week04_evrp_tw_output.txt`

---

### Week 3 — 2026-07-07 (completed in catch-up sprint)

**Attended this week's meeting:** No (family circumstances — leave to be emailed)

**Progress this week**
- **Reproduced the baseline on a standard benchmark** instead of only a toy instance (`src/experiments/week03_reproduce.py`).
- Loaded a Solomon-format VRPTW instance (`src/data/solomon_c101_small.txt`, 6 nodes, wide time windows) and solved it with OR-Tools.
- Result: **FEASIBLE**, objective (total distance) = **54**, runtime ≈ 5.0 s, 1 vehicle used (load 100/200).
- Output: `src/results/week03_reproduce_output.txt`.

**Challenges & blockers**
- None major; the Week 1 VRPTW code transferred directly to the standard format.

**Next steps**
- Use this reproducible baseline as the comparison point when adding EVRP-TW (Week 4) and the learning/hybrid method (Week 6–7).

**Hours spent (optional):** 10h (plus shared catch-up time)

**Links (optional):** `src/experiments/week03_reproduce.py`, `src/data/solomon_c101_small.txt`, `src/results/week03_reproduce_output.txt`

---

### Week 2 — 2026-06-22

**Attended this week's meeting:** No (family circumstances — leave emailed: Yes)

**Progress this week**
- Studied Python and part of the machine-learning / RL background (programming foundation was weak at the start).
- Looked at POMO but did **not** finish; only did basic learning.
- *Retrospective (2026-07-07):* POMO was the wrong entry point. The project Lab reserves POMO/RL for students who already understand CVRP + neural training. Switched to the OR-Tools **classical VRPTW** path, which is now the foundation for Weeks 1–5.

**Challenges & blockers**
- Paper reading took a long time; many concepts were unfamiliar.
- Spent time on POMO/ML without ever running a solver — this is what caused the slide in progress.

**Next steps**
- Stay on the classical OR-Tools path; build EVRP-TW and truck-drone on top of it (done in the catch-up sprint).

**Hours spent (optional):** 15h

---

### Week 1 — 2026-06-13

**Attended this week's meeting:** Yes

**Progress this week**
- Set up the repository from the FURP template.
- *The Week 1 baseline smoke test (required deliverable) was actually completed on 2026-07-07 during the catch-up sprint* — see `docs/week01_checkpoint.md`.
- Baseline: small VRPTW (1 depot + 5 customers, 2 vehicles) solved with OR-Tools → **FEASIBLE**, objective (total distance) = **108**, runtime 0.005 s (greedy) / 3.0 s (local search). Code: `src/experiments/week01_baseline.py`; output: `src/results/week01_baseline_output.txt`.

**Next steps**
- Move to literature + data formats (Week 2) and baseline reproduction on a standard instance (Week 3) — both done in the catch-up sprint.

**Hours spent (optional):** 10h (setup) + 3h (baseline, 2026-07-07)
