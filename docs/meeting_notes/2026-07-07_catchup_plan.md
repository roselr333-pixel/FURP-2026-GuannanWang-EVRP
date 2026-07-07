# Meeting Note — Catch-up Plan (2026-07-07)

**Participants:** Guannan Wang (student), WorkBuddy (assistant)
**Type:** Project recovery / planning session

## Key takeaways

1. **Diagnosis:** The project is on the Week 5 timeline, but the Week 1 deliverable
   (baseline smoke test) was never completed. Previous weeks were spent learning
   Python/ML basics and looking at POMO without running any solver.
2. **Root cause:** POMO / deep-RL was treated as the entry point. The project Lab
   explicitly says POMO is only for students who already understand CVRP + neural
   training. For a weak programming background, **OR-Tools classical VRPTW is the
   correct starting baseline**.
3. **Decision:** Stay on the classical path:
   VRPTW baseline → add battery/charging (EVRP-TW) → truck-drone → hybrid/learning.

## Action items

| # | Action | Owner | Target | Status |
|---|--------|-------|--------|--------|
| 1 | Week 1 OR-Tools VRPTW baseline (objective 108, FEASIBLE) | Guannan | 2026-07-07 | ✅ DONE |
| 2 | Reproduce baseline on a standard benchmark (Solomon instance) | Guannan | Week 3 | ✅ DONE (obj 54) |
| 3 | Add battery + charging → EVRP-TW; violation table | Guannan | Week 4 | ✅ DONE |
| 4 | Choose cited paper to replicate | Guannan | Week 4 → deferred to 2026-07-08/09 | ⏳ deferred |
| 5 | Truck-drone synchronization model | Guannan | Week 5 | ✅ DONE (heuristic) |
| 6 | Hybrid/learning method + ablation vs baseline | Guannan | Week 6–7 | ⏳ pending |
| 7 | Final report, slides, demo video, poster | Guannan | Week 8 | ⏳ pending |

## Notes / risks

- Attendance: Week 5 meeting **confirmed (attended)**. Weeks 2–4 meetings missed
  due to family circumstances — **leave emails have already been sent (confirmed)**.
- The cited paper (action #4) is **deferred to 2026-07-08/09**; this gates the
  final "replication + 10% innovation" requirement for certification.
- **Paper reading notes are also deferred** — the student will add them after
  reading the papers (planned 2026-07-08/09).
- **POMO / GA baselines are deferred to a later stage** (per current plan), not
  attempted yet.
- Do **not** jump to POMO or truck-drone until the classical baseline is reproduced
  on a standard instance with logged objective / feasibility / runtime.
