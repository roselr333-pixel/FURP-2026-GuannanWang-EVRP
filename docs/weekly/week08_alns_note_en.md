# ALNS on the physical FSTSP model (the search side)

> Written 2026-09-13. The exact-optimality study
> (`docs/weekly/week08_exact_gap_note_en.md`) found that from n=10 on the CP-SAT
> model's own feasible plan is 8.8–17.5% better than what my LNS finds, and drew the
> conclusion that the lever is the search rather than more solver time. This note
> takes that up: a proper ALNS on the same physical model.

## 1. What was weak

`week08_lns` destroys at most `min(8, n // 4)` customers — **2** of them at n=10 —
and repairs with a single greedy rule, with a fixed operator mix. A destroy that
small cannot escape the local optimum of one insertion order.

## 2. The ALNS

- **destroy (5)**: random; worst (ranked by the exact removal gain); related (Shaw:
  grow a set from a seed customer, always adding the one closest to the set); route
  segment; whole drone sorties.
- **repair (2)**: cheapest insertion; regret-2 (insert first the customer whose
  second-best option is furthest from its best).
- Destroy size `max(2, 0.35 n)`; budget `100 n` iterations; simulated-annealing
  acceptance with the initial temperature at 6% of the current makespan cooled to
  0.2% of that.
- **Adaptive operator weights** every 120 iterations (`rho = 0.30`, scores 12/6/2
  for a new best / an improvement / an accepted worse solution), plus an
  `adaptive=False` switch that freezes them — the ablation in §4.
- Every candidate is evaluated with `cpsat_fstsp.fstsp_makespan_clean`, i.e. the
  same physical model and the same objective as the exact study, so the comparison
  against the CP-SAT primal plan is like for like.
- The ALNS starts from the LNS solution and is deterministic given the seed and the
  iteration budget.

## 3. Results (5 seeds × N = 8/10/12/14/16, mean over seeds)

| N | greedy | LNS | **ALNS** | ALNS vs LNS (range) | frozen weights | adaptive vs frozen | CP-SAT best feasible | ALNS vs CP-SAT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 251.2 | 224.7 | **218.7** | +2.8% (0.0–9.3) | 216.3 | −0.95% | 193.3 | +13.2% |
| 10 | 364.1 | 291.3 | **272.1** | +6.7% (0.0–11.7) | 272.5 | +0.18% | 239.9 | +13.4% |
| 12 | 430.9 | 358.5 | **331.5** | +7.2% (0.0–14.5) | 329.9 | −0.53% | 298.3 | +11.1% |
| 14 | 510.3 | 439.5 | **384.6** | +12.2% (8.0–18.9) | 387.5 | +0.63% | 367.7 | +4.8% |
| 16 | 573.3 | 462.2 | **449.5** | +2.7% (0.0–6.5) | 440.3 | −2.13% | 426.8 | +6.8% |

Makespan in physical FSTSP time units; the CP-SAT column is the best feasible plan
that run found (proven optimal only at n=8). Figure `figures/alns_fstsp.png`,
per-instance rows in `src/results/week08_alns_raw.csv`.

## 4. What it shows

1. **The search had room and the ALNS takes most of it.** Against the LNS it is
   2.7%–12.2% shorter — mean **+6.3%** over the five sizes — and at n=14 the gain is
   +8.0%–18.9% with no instance left unchanged. At n=8 the gap to the *proven*
   optimum falls from 16.5% (LNS) to **13.1%**.
2. **The adaptivity does not pay here** (the honest negative result): with the same
   budget and the same seed, freezing the operator weights is as good or better at
   n=8/12/16 (−0.95%, −0.53%, −2.13%) and only marginally worse at n=10/14 (+0.18%,
   +0.63%). The gain comes from the destroy size and the operator set, not from
   credit assignment. The adaptive code stays in the module and is tested, but the
   improvement does not rest on it.
3. **The CP-SAT primal is still ahead on average**, ALNS 4.8%–13.4% above it, so the
   two are complementary rather than one replacing the other: on n=14 seed
   20260723 the ALNS wins (367.7 against 369.8), elsewhere the exact model's plan is
   better. Only n=8 is proven optimal, so which of them is closer to the optimum
   stays open — and at n=8 neither is at it (the ALNS is 13% above).
4. **The budget matters where the search is still moving**: on n=8 seed 20260722 the
   ALNS goes 224.7 → 212.4 → 208.9 at 800 / 3000 / 10000 iterations, while on seed
   20260720 it reaches 165.7 (4.6% above the optimum) and then stops moving
   altogether. The reported budget is `100 n`, so the small-n rows above are the
   conservative end of what this search can do.

## 5. Limitations

- One start only (the LNS solution); no restarts from other constructions.
- No time windows, battery or capacity in this model — it is the FSTSP model the
  exact study uses, so these numbers do not transfer to V3 as they are.
- Parameters (`Q_FRAC`, segment length, scores, cooling) are hand-set. The
  destroy-size probe (0.35 / 0.50 / 0.70 on n=8 seed 20260722: 224.70 / 224.93 /
  226.81, and 288.95 three times on n=12 seed 20260720) says 0.35 is enough and
  larger destroys only cost time.
- The comparison against CP-SAT is against its feasible plans, not against the
  optimum, and only n=8 is proven.

## 6. Artifacts

- `src/experiments/alns_fstsp.py` — the ALNS, the operator sets and the runner
- `tests/test_alns.py` — 16 tests: every customer served once, the plan physically
  valid, never worse than its start, deterministic, and each destroy/repair operator
- `src/results/week08_alns_raw.csv` / `_summary.csv` / `_log.txt` (plus the console
  transcript `week08_alns_run.log`)
- `src/tools/gen_alns_figure.py` → `figures/alns_fstsp.png`
- reference: `src/experiments/week08_exact_gap.py` (the CP-SAT primal and the proven
  n=8 optima), `src/experiments/week08_lns.py` (the LNS this improves on)
