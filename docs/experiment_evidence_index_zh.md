# 实验证据索引（Experiment Evidence Index）

> 目的：把本项目所有**可引用数值**集中到一页，附数据出处与局限，便于核对与引用。
> 所有数据均来自本项目自己的脚本与 CSV（`src/results/` 下），不含任何同学报告的结构或框架。
> 配套文档：`docs/week06_depth_analysis_zh.md`（把下面这些数串成"为何有效、何时有效"的结论链）。

---

## 1. 三基线对比（纯卡车 VRPTW，56 个 Solomon 实例 vs BKS）

出处：`src/results/baseline_consolidated.csv` / `_summary.csv`（由 `baseline_consolidated.py` 生成）。

| 基线 | 相对 BKS 平均 gap | 角色 |
|---|---:|---|
| **PyVRP**（领域标准开源求解器） | **−3.0%** | 最强基线，社区公认 |
| OR-Tools（商业求解器） | +7.2% | 主要对照基线 |
| GA（自写，5 种子均值） | +36.6% ± 15.8% | 自写元启发，性能弱于前两者 |

按算例族（gap vs BKS，PyVRP / OR-Tools / GA）：

| 族 | n | PyVRP | OR-Tools | GA(±std) |
|---|---:|---:|---:|---:|
| C1 | 9 | −2.3% | +4.2% | +25.9% ± 24.2% |
| C2 | 8 | −4.3% | +0.9% | +36.0% ± 16.3% |
| R1 | 12 | −3.2% | +5.1% | +31.2% ± 8.2% |
| R2 | 11 | −3.5% | +12.4% | +41.5% ± 6.0% |
| RC1 | 8 | −2.2% | +6.4% | +30.6% ± 2.4% |
| RC2 | 8 | −2.1% | +13.7% | +56.8% ± 5.1% |

V2 是协同启发式，优化的是 makespan 驱动的同步目标，其"距离"不直接与这些纯距离最小化基线比较。将它们并列，是为了说明在标准卡车 VRPTW 上 PyVRP 能打到甚至略优于 BKS；本项目的增量在协同建模，而非单目标距离优化。OR-Tools 用 GUIDED_LOCAL_SEARCH、10 秒上限，本身是随机的，重跑约有 ±0.1 pp 波动（下表数字来自合并 CSV）。

---

## 2. 参数敏感性（5 种子均值 ± 标准差，n=12 除规模扫描外）

出处：`src/results/week06_sensitivity.csv` + `figures/sensitivity_panels.png`（由 `week06_sensitivity.py` 生成；2026-09-10 修复续航 R 参数未生效的 bug 后重跑）。

benefit = (V1 纯卡车距离 − V2 协同距离) / V1 距离 × 100%。

| 参数 | 扫描 | 协同收益（均值 ± std） | 解读 |
|---|---|---|---|
| 电池 Q | 120→500 | 55.8%→47.1%（±~9.7） | 电池越大，卡车越"自给"，无人机价值被稀释 |
| **续航 R** | 60→200 | **15.5%→27.7%→35.2%→50.5%@160→48.7%@200** | 续航 <160 是真实瓶颈；160 后饱和 |
| 每架次客户 K | 1→3 | 25.3%→50.5%→56.5%（±8.6~16.5） | 多顾客能力是主增益，与消融一致 |
| 规模 N | 8→30 | 63.8%→35.3%（±6.7~12.5） | 规模越大协同收益越被稀释 |

> 注：R 扫描在 2026-09-10 前因 `mk_range` 未把续航传给模型而恒为 50.5%（错误）；修复后如上，与深度文档 §2 叙述一致。

---

## 3. 多目标权衡（距离 vs 时长，加权和扫描）

出处：`src/results/week06_multi_objective.csv` + `figures/mo_*.png`（由 `week06_multi_objective.py` 生成）。

| 变体 | 距离均值 | 时长均值(makespan) |
|---|---:|---:|
| V1 纯卡车 EV | 486.4 | 622.4 |
| V2 协同（全部 w×种子均值） | 215.2 | 415.7 |

- 距离 **−56%**、时长 **−33%**，V2 在**两个轴同时占优** V1（逐种子核对均成立）。
- 权重 w ∈ {0, 0.25, 0.5, 0.75, 1.0}，5 种子；w 越大越偏距离、时长越长。
- **局限**：用加权和标量化的贪心，不是完整 NSGA-II / Pareto 求解器，给出的前沿是"粗"的——这是方法局限，不是卖点。

---

## 4. 受控消融（5 配置同台，40 算例，size 8/12/16/20）

出处：`src/results/week07_ablation_summary.csv`（由 `week07_improvement_ablation.py` 生成）。

V2 相对纯卡车(Truck-only)的 makespan 改善：size 8 → 39.2%、12 → 37.8%、16 → 32.4%、20 → 29.9%。

增益分解（各 size 的 pp 贡献）：

| 增益来源 | 范围 | 结论 |
|---|---|---|
| **多顾客能力**（max_cust 1→2–3） | **+6.6 ~ 17.7 pp** | **主增益源** |
| 多次起降（multi-takeoff） | +4.1 ~ 7.3 pp | 次增益 |
| cap3（每架 3 顾客） | +2.3 ~ 8.7 pp | 多顾客能力的上限延伸 |

sanity check：abl_cap1（每架 1 顾客）≡ published(M&C 2015) 已发表启发式，证明框架一致。

---

## 5. 规模衰减（N=30 / 50，5 种子）

出处：`src/results/week06_largeN_summary.csv`（由 `week06_largeN.py` 生成）。

| 规模 | V2 vs V1 收益 | 卸载率 | 会合否决数 | 平均 TW 违例 |
|---|---:|---:|---:|---:|
| N=30 | 27.6% | 62.0% | 33.7 万 | 8.0 / 30 |
| N=50 | 12.1% | 42.8% | 453.5 万 | 24.0 / 50 |
| N=100 | 2.3% | 23.4% | 1.795 亿 | 71.4 / 100 |

N=50 时 V1（电池+充电）代价 ≈ 5670 vs V0（无电池）≈ 3094——电池约束本身在 N≥30 给卡车加近一倍代价，V2 无人机能绕开的充电路径有限，协同收益被稀释。到 **N=100** 协同收益坍缩至 2.3%、卸载率降至 23.4%、V2 平均 **71.4/100 顾客超时**（贪心本就不保证 TW 可行，`feasible` 仅指能量可行）；规模边界见 `figures/largen_scale_decay.png`，结论是**有效协同区间落在 N ≤ 50**。

---

## 6. 失败案例（17 条，1 条严格不可行）

出处：`docs/failure_cases_master.md`。最值得说的一条：N=50 密集算例上**会合可行性否决约 450 万次**，说明同步会合约束在大规模是主要瓶颈——与第 2、5 节的"规模越大收益越稀释"互相印证，共同划定方法适用边界。

---

## 7. Schneider (2014) E-VRPTW 复现（构造式贪心 vs BKS）

出处：`src/results/schneider_evrptw_baseline.csv`（自写求解器，92 实例）与
`src/results/schneider_evrptw_bks_comparison.csv`（18 个有 BKS 的实例：5 顾客 C5 集取自
jmanzolli/E-VRPTW 引 Schneider 2014；100 顾客 _21 集取自 Adachi et al. 2022 引 Schneider 2014）。
自写求解器是带同质多程车队的构造式贪心（先最小化车辆数、再最小化距离），在载重 + 时间窗
（允许等待）+ 充电站满充下做可行性检查。图：`figures/schneider_routes.png`（4 个代表实例的
路线地图，每面板标注 BKS 距离与车辆差距）、`figures/schneider_vehcomp.png`（18 实例车辆数 my vs BKS）。

**局限**：BKS 路线几何未公开（次级文献只给距离值），所以对比在聚合层（距离 + 车辆数），
而非无法制作的路线几何叠加。我的 92 个实例已与 jmanzolli/E-VRPTW 原版实例逐文件核对
（仅空白差异），确认就是 Schneider 原版数据。求解器自 2026-09-10 起是确定的（顾客集按 ID
排序迭代，消除 Python 每进程哈希随机化），因此下列数字重跑可精确复现。

聚合（18 个有 BKS 的实例）：
- 平均距离差距 **+50.7%**（绝对值均值；有符号均值 +50.1%；构造式贪心 vs Schneider/Adachi BKS）。
- 平均车辆数：我方 **5.4** vs BKS **2.1**（差距 **+3.4**；差距最大在 100 顾客 _21 集——c201_21
  车辆差距达 +12——那里需要 ALNS 级方法才能把顾客并成 BKS 的少数车辆；构造式贪心无法全局安排
  多程车辆，因为后发的趟次出发太晚、赶不上早时间窗）。
- 个别 C5 小赢：c103C5 −0.4%、r105C5 −4.4%（在少数小规模/宽松时间窗实例上我方贪心有竞争力；
  大损失都在 100 顾客 + 紧时间窗实例上）。

---

## 8. 局限

按性质分三组；每条都给「后果 + 下一步」，避免写成单纯的弱点清单。

**模型假设边界**
- **每架次 2–3 顾客**：这是有意的简化，也划出了方法边界。无人机多顾客服务用 O(n⁴) 枚举，规模一大就不可行；要支持更多顾客需更轻量的搜索（如先聚类再分配）。更大的多顾客协同属于未来工作。
- **V2 尚未叠回 V1 的电池/充电层**：卡车-无人机模型（V2）在 VRPTW 上建模，未把 V1 的电动车电池与充电约束重新纳入；真正「电动卡车 + 无人机 + 充电站」联合优化是明确的下一步。

**算法能力边界**
- **贪心无局部搜索**：对 V2 构造出的卡车路线再做 intra-route 2-opt（仅接受严格改善 makespan），增益仅 0–1.76%（N=16 峰值 1.76%，见 `week07_fstsp_with_ls.log`）。对照之下，纯 OR-Tools 路线上的 2-opt 在 CVRP n40 能到 −9.7%——说明 V2 的增益来自「无人机卸掉远端顾客」的协同结构，而非路线微调；也意味着 V2 已接近当前邻域的局部最优。**离全局最优多远仍不可量化**（除非加 MILP 上界或 3-opt 等更大邻域），留作后续。

**实验验证边界**
- **合成算例规模扩展到 100，但有效协同区间落在 N ≤ 50**：我的卡车-无人机实验用随机几何生成的合成算例，未接入领域常用的标准大规模基准集（如 Murray & Chu 2015 基于 Solomon 派生的 FSTSP 算例——本项目 W7 已在其参数范围内复现；或 Masmoudi et al. 2018 的实例集）。N=100 时协同收益坍缩至 2.3%、V2 平均 71.4/100 顾客超时（TW 可行性崩溃），结论向真实大规模外推需谨慎。
- **未复现 MILP 下界**：基线对比用 BKS（文献最优）锚定，而非自证下界。对这个 NP-hard 问题求精确下界本身是一份独立的研究贡献，超出本项目范围；因此绝对质量靠文献锚定，不是自证。
- **多目标为粗前沿**：加权和贪心给出的是「部分/内点」前沿，可能漏掉非凸区域的 Pareto 点；它不是完整的 Pareto 求解器（见 §3）。要得完整前沿，自然的下一步是 ε-constraint 或 NSGA-II（同侪 Xie 的 P-ACO/NSGA-II 即此类）。

---

## 9. 数据出处一览（可直接重跑）

| 结果 | 脚本 | CSV | 图 |
|---|---|---|---|
| 三基线 | `baseline_consolidated.py` | `baseline_consolidated.csv` / `_summary.csv` | `baseline_consolidated.png` / `pyvrp_family_gap.png` |
| PyVRP 基线 | `baseline_pyvrp_vrptw.py` | `baseline_pyvrp_vrptw_results.csv` | `pyvrp_family_gap.png` |
| GA 基线 | `baseline_ga_vrptw.py` | `baseline_ga_vrptw_results.csv` | — |
| 敏感性 | `week06_sensitivity.py` | `week06_sensitivity.csv` | `sensitivity_panels.png` |
| 多目标 | `week06_multi_objective.py` | `week06_multi_objective.csv` | `mo_scatter.png` / `mo_tradeoff.png` |
| 消融 | `week07_improvement_ablation.py` | `week07_ablation_raw.csv` / `_summary.csv` | — |
| 规模 | `week06_largeN.py` | `week06_largeN_results.csv` / `_summary.csv` | `largen_scale_decay.png` |
| Schneider 复现 | `schneider_evrptw.py` + `schneider_bks_compare.py` + `plot_schneider_routes.py` | `schneider_evrptw_baseline.csv` / `schneider_evrptw_bks_comparison.csv` | `schneider_routes.png` / `schneider_vehcomp.png` |
| FSTSP 复现 | `week07_fstsp_repro.py` | `week07_fstsp_raw.csv` / `_summary.csv` | — |

种子约定：所有多种子实验都用固定种子集（如 `20260910–20260914`，或 GA 的 `20260717/20260801/20260815/20260901/20261001`）以保证可复现；CSV 按设计不入库，靠脚本 + 种子在本地重新生成。

随机种子约定：所有"多种子"实验用固定种子集合（如 `20260910–20260914` 或 GA 的 `20260717/20260801/20260815/20260901/20261001`），保证可复现；CSV 按仓库约定不入库，靠脚本+种子本地重跑生成。
