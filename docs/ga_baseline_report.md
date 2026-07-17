# GA Baseline Report — Official Solomon VRPTW (100-customer set)

> - Author: Guannan Wang (student)
> - Date: 2026-07-17
> - Scope: a self-implemented Genetic Algorithm added as an *external baseline* next to OR-Tools, evaluated on the same 56 official Solomon instances used in `benchmark_official_solomon.py`.
> - Note: this is a classical metaheuristic I wrote as a small exercise, mainly to get some basic hands-on experience with how a heuristic is built. It is **not** a paper reproduction and is **not** intended to compete with OR-Tools.

## 1. Why I added a GA baseline

My Week-5 work uses OR-Tools (guided local search) as the main solver, and I compared it against the official 56-instance BKS (mean gap 7.2%). OR-Tools works well, but using it alone does not give me much hands-on sense of how a routing heuristic is actually built. So I tried writing a Genetic Algorithm myself and running it on the **same** instances, so any comparison is at least on identical data and identical BKS.

## 2. How the GA is built

| Component | Choice | Why |
|---|---|---|
| Encoding | customer permutation (route-first) | simplest, classic GA representation |
| Decoding | Solomon I1 insertion | gives a *feasible* route set (capacity + time windows) and tends to use few vehicles |
| Fitness | total distance + bidirectional vehicle penalty + `force_fleet` split | tries to make GA compete on distance at the **same fleet size** as BKS (otherwise wide-window instances would use fewer vehicles and look artificially better) |
| Selection | tournament (size 4) + elitism (6 copied) | keeps the best, still explores |
| Crossover | Order Crossover (OX) | standard permutation operator |
| Mutation | swap + reverse, rate 0.3 | local perturbation |
| Local search | intra-route 2-opt + inter-route relocate | polishes each individual |
| Warm start | Clarke–Wright savings seed | a reasonable starting point; it worked well on the clustered (C-type) instances |
| Budget | pop=40, 8 s per instance, fixed seed 20260717 | keeps the full 56-instance run under ~11 min |

## 3. Results

**Solved 56/56. GA mean gap to BKS = 36.2%.** (For reference, OR-Tools mean gap on the same set = 7.2%.)

Per-family mean gap (GA vs BKS):

| Family | n | mean gap | min | max |
|---|---|---|---|---|
| C1 | 9 | 29.1% | 0.2% | 90.6% |
| C2 | 8 | 31.5% | 0.4% | 61.9% |
| R1 | 12 | 31.7% | 15.2% | 45.9% |
| R2 | 11 | 41.0% | 32.6% | 57.5% |
| RC1 | 8 | 29.9% | 19.5% | 39.3% |
| RC2 | 8 | 55.1% | 35.0% | 68.9% |

## 4. What the numbers tell me

- **GA is worse than OR-Tools on every instance** (`ga_minus_ortools_gap` is positive for all 56). This is expected: OR-Tools uses industrial-grade guided local search, while my GA is a basic textbook metaheuristic.
- **High variance on clustered instances.** C101 / C105 / C106 come within 0.2% of BKS (close to OR-Tools), but C103 blows up to 90.6%. The savings seed helped the easy clustered cases but hurt stability elsewhere — a real weakness worth noting.
- **Wide time windows (R2 / RC2) are hardest** (41% / 55%). With only 8 s and a basic local search, the GA barely converges on these looser, more combinatorial instances.
- A side observation: on many R/RC instances OR-Tools itself uses *fewer* vehicles than BKS while paying more distance — that is the vehicle-fixed-cost modelling I noted in the checkpoint, not a GA issue.

## 5. Limitations (honest)

- Single run, single seed, only 8 s/instance — GA results are stochastic and the budget is small.
- No parameter tuning; local search is basic.
- It is a generic VRPTW heuristic, **not** adapted to the E-VRPTW charging constraints that are the actual focus of my project.

## 6. Conclusion & next step

The GA baseline was a useful first attempt. It is clearly weaker than OR-Tools, but it gave me a rough point of reference when looking at my own results. It is not a paper reproduction, and the interesting question for me is not "can I beat OR-Tools with a toy GA" but "how do published E-VRPTW methods (Schneider 2014, Murray & Chu 2015) compare, and can I reproduce them?" — which is the paper-reproduction track I will start once I have those two PDFs.

Files produced: `src/results/baseline_ga_vrptw_results.csv`, `src/results/baseline_ga_vrptw_comparison.csv` (GA vs OR-Tools vs BKS), `src/results/baseline_ga_vrptw_output.txt`.
