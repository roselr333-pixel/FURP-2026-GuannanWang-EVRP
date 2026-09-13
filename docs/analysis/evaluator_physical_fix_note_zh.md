# 主评估器物理化修正（W7/W8 + W6 重跑说明）

## 1. 改了什么

`week07_fstsp_repro.fstsp_simulate`（以及多无人机版 `fstsp_simulate_multi`）是 W7/W8 卡车-无人机实验共用的完成时间评估器。原版用 `drone_avail` 把多个架次串行化，但**不检查无人机是否已经回到卡车**：当一个架次嵌套在另一个架次内部（例如 A 从 0 飞到 2，B 在路线中段 12→10 之间起降）时，它仍然给出一个 makespan，而这样的计划物理上不可实现——一架无人机不可能同时飞两个重叠架次。

现在评估器强制执行物理有效性：

- 发射节点必须在回收节点之前（卡车行进方向上）；
- 每架次的飞行总长 ≤ 航程 `R_D`；
- 发射时无人机必须已经在卡车上（上一个架次已回收，卡车已等到）；
- 不满足任一条，返回 **inf**（计划不可行）而不是给出一个 makespan。

因为启发式（`my_v2_param`、`fstsp_insertion`、LNS）都用这个评估器判定一个候选移动是否改善，返回 inf 后它们会**自动拒绝**会造成嵌套的移动，因此产出的解天然是物理可行的。

## 2. 影响范围

凡经过 `fstsp_makespan` / `fstsp_makespan_multi` 的实验都受影响，已全部重跑：`week07_fstsp_repro`、`week07_improvement_ablation`、`week08_lns`、`week08_multidrone`、`week08_multidrone_std`（含 `week08_scheduling.csv`）、`week06_sensitivity`、`week06_multi_objective`、`stat_tests`，以及 `week08_exact_gap` 的"原始 V2"一列。相关图（`lns_vs_greedy`、`multidrone`、`multidrone_std`、`sensitivity_panels`、`mo_*`）已重新生成。

## 3. 旧口径 → 新口径

| 指标 | 旧（非物理评估器） | 新（物理评估器） |
|---|---|---|
| V2 相对 M&C 2015（W7） | 短 8–22% | 短 **10.2–14.2%** |
| V2 相对 truck-only（消融，N=8/12/16/20） | 39.2 / 37.8 / 32.4 / 29.9% | **34.5 / 29.0 / 28.7 / 24.8%** |
| 多顾客能力增益 | +6.6~17.7 pp | **+8.6~12.1 pp** |
| 多次起降增益 | +4.1~7.3 pp | **+2.2~4.4 pp** |
| `abl_cap1 == published`（sanity check） | 通过 | **仍通过（逐实例精确相等）** |
| LNS 相对贪心 | +9~12.6% | **+12.5~21.3%** |
| 2-opt 相对贪心 | 0–1.76% | **2.5–3.1%** |
| 多无人机（N=50，K=1 → K=3，vs truck） | 28.1% → 36.0% | **29.5% → 38.1%** |
| 标准算例（N=10 / N=50，K=5） | 71.4% / 48.6% | **71.4% / 46.8%** |
| 调度：可证朴素规则最优的配置数 | 31/64 | **64/64** |
| 调度：local 相对朴素规则增益 | +0.001% | **0.000%** |
| Wilcoxon：V2 vs 已发表 M&C | n=40，−73.0，p=5.9×10⁻⁷ | **n=38，−73.2，p=2.4×10⁻⁷** |
| Wilcoxon：LNS vs 贪心 | n=46，−146.2，p=3.6×10⁻⁹ | **n=54，−194.3，p=1.7×10⁻¹⁰** |
| 敏感性：电池 Q（120→500） | 55.8% → 47.1% | **41.2% → 29.7%** |
| 敏感性：续航 R（60→160→200） | 15.5% → 50.5% → 48.7% | **15.4% → 34.4% → 34.4%** |
| 敏感性：每架次顾客 K（1→3） | 25.3% → 50.6% → 56.5% | **20.5% → 34.4% → 37.1%** |
| 多目标：距离 / 时长（V2 vs V1） | −56% / −33% | **−32% / −34%** |
| W6 主线 V2 vs V1（N=8/12/16/20） | 50.5 / 55.3 / 53.9 / 42.1% | **33.6 / 24.5 / 19.6 / 15.6%** |
| W6 卸载率（N=8/12/16/20） | 65.0 / 70.8 / 71.9 / 67.0% | **31.2 / 21.7 / 18.1 / 14.5%** |
| 规模衰减 V2 vs V1（N=30/50/100） | 27.6% → 12.1% → 2.3% | **8.6% → 3.4% → 0.5%** |
| 规模衰减卸载率（N=30/50/100） | 62.0% → 42.8% → 23.4% | **11.3% → 5.2% → 2.6%** |
| Wilcoxon：V2 vs V1（协同 vs 纯电） | n=40，−424.3，p=3.7×10⁻⁸ | **n=40，−182.1，p=3.71×10⁻⁸** |

要点：

- **结论方向不变，幅度下调**。V2 仍优于已发表的 M&C 启发式（10–14%），改进方向与消融归因（多顾客能力是主增益源）都仍然成立；`abl_cap1` 与 published 仍逐实例精确相等。
- **调度那一节的性质变了**：物理化之后，单架/多架 LNS 产出的架次集合不再重叠，K 架无人机的调度不再有竞争，于是朴素"最早可用"规则在全部 64 个配置上可证最优、local 增益为 0。原先"31/64 可证 + 局部搜索略有增益"是嵌套架次制造的假竞争。
- 旧口径下调最多的两项是电池敏感性与多目标距离维度（55.8%→41.2%、−56%→−32%），因为它们直接依赖评估器压低的 makespan。

## 4. 第二轮：week06 评估器物理化（同日）

`week06_ground_air_evrp_tw.py` 原本有自己的 `simulate`：它把每个架次的降落时刻独立取最大值（`drone_free = max(...)`），既不检查无人机是否已经回到卡车，也不做架次串行，因此嵌套/交叉架次同样会被赋一个 makespan——比修正前的 `fstsp_simulate` 还宽松。W6 的 V0/V1/V2 主结果与 `week06_largeN`（规模衰减）走的是这条路径。

这一轮把它改成与 `fstsp_simulate` **同一套物理语义**：

- 架次按起飞位置排序后逐个模拟；
- 起飞点必须在回收点之前；
- 单架次航程不超过 `R_D`；
- 上一架次回收之前不能起飞（一架无人机同一时刻只执行一个架次）；
- 无人机晚到则卡车在回收点等待，等待量顺延到后续所有到达时刻；
- 违反任一条返回 `inf`。

同时把 `collaborative` 的接受准则从「移除客户能降低**卡车** makespan」改成「**加上这架次后整条计划的 makespan 变小**」，并对候选架次加上单机串行的位置检查。两处合起来保证启发式不会产出评估器会拒绝的计划（重跑后 `V2_plan_valid_rate = 1.0`）。

对齐验证：用 400 个随机路线 + 随机架次集合，`week06_ground_air_evrp_tw.simulate` 与 `week07_fstsp_repro.fstsp_simulate` 的 makespan 逐一相等（不可行判定也一致），回归测试见 §6。

影响范围：`week06_ground_air_evrp_tw`（主线）、`week06_largeN`、`stat_tests` 的 "V2 vs V1" 一行已全部重跑；V0/V1 不涉及无人机，数值逐位不变（例如 N=50 的 V1 仍是 5661.9）。`week06_sensitivity` 与 `week06_multi_objective` 走的是 `fstsp_makespan`，不受这次改动影响。新旧数字见 §3 后 5 行。结论方向同样不变：协同收益仍随规模单调衰减，而且塌得更快（N=50 只剩 3.4%），有效协同区间收窄到 N ≤ 30。

## 5. 第三轮：无人机调度可用性检查（V3 / W5 / M&C）

前两轮之后又发现同一类缺陷的第四处：**评估器在发射时不检查分配到的无人机是否已经回到卡车**。

- `v3_ev_collab.ev_collab_k` 已经按 `avail[d]` 串行分配，但 `launch = max(arr[i_pos], avail[d])` 在无人机未就位时只是把发射推迟到它空闲，而卡车早已离开那个节点；同时 `v3_greedy` 的候选枚举也不要求架次区间互不重叠。实测 V3 的 **40/40** 个算例都产出了物理不可行的架次集合。
- 同一缺陷也在 `week05_truck_drone_v2.simulate`（`drone_free = max(...)`，与第一轮的 `week06` 同形）、`fstsp_mc.mc_simulate`（M&C 原始算例基准）与 `drone_scheduling.simulate`（W8 调度）里出现。

修法：四处评估器都补上"发射时无人机必须在卡车上"（`avail[d] > arr[i_pos]` 或回收点在发射点之前 → 不可行），`v3_greedy` 再加一道架次区间不重叠的预筛。

重跑后的变化：

| 指标 | 旧 | 新 |
|---|---|---|
| V3 单架 LNS 降幅（K=1） | 34.7%~53.4% | **33.5%~52.4%** |
| V3 贪心 V3g 降幅 | 27.9%~46.4% | **16.3%~39.2%** |
| V3 消融：多顾客能力（N=8/12/16/20，pp） | +16.4 / +19.4 / +9.5 / +1.7 | **+12.5 / +8.5 / +10.9 / −2.8** |
| W5 v2 flexible makespan（6 顾客） | 277.3（−49.8% vs truck-only） | **318.9（−17.9%）** |

W5 那一行还牵出两个相关问题：`depot_only_drone` 用卡车速度给无人机计时、并且用了与 `week05_truck_drone.py` 不同的巡回构造，导致同一基线在两个脚本里分别给出 389.5 与 270.6；两处都修好后两个脚本一致（270.6）。另外在修正后的单机物理口径下，W5 的"任意节点起降"变体在这个 6 顾客算例上**慢于**"无人机独立跑仓库巡回"的 v1 模型（318.9 对 270.6）——携带式模型的价值要到 W6–W8 的更大规模才体现。

结论方向不变：V3 的协同收益仍显著（K=1 33.5%~52.4%，K=2/3 到 44.5%~72.5%），V3 消融也仍指向"多顾客能力是主增益源"（+8.5~12.5pp，N=20 转为 −2.8pp）。

## 6. 产物

- 第一轮改动：`src/experiments/week07_fstsp_repro.py`（`fstsp_simulate` / `fstsp_simulate_multi`）
- 第一轮回归测试：`tests/test_evaluators.py::test_heuristic_plans_are_physically_valid`（启发式的解必须物理可行，且与 `cpsat_fstsp.fstsp_makespan_clean` 数值一致）
- 失败案例：`docs/reference/failure_cases_master.md` 的 FC-7-4（现已修正）
- 第一轮重跑的日志与 CSV：`src/results/week07_*`、`week08_*`、`week06_sensitivity*`、`week06_multi_objective*`、`stat_tests*`
- 第二轮改动：`src/experiments/week06_ground_air_evrp_tw.py`（`simulate` / `collaborative` / `run_variant` / 汇总列）
- 第二轮回归测试：`tests/test_evaluators.py::test_w6_evaluator_rejects_overlapping_sorties`、`::test_w6_evaluator_rejects_out_of_range_sortie`、`::test_w6_truck_waits_for_a_late_drone`、`::test_w6_evaluator_matches_shared_fstsp_evaluator`、`::test_w6_collaborative_plan_is_physically_executable`
- 第二轮重跑的日志与 CSV：`src/results/week06_ground_air_*`、`week06_largeN_*`、`stat_tests*`
- 第三轮改动：`src/experiments/v3_ev_collab.py`（`ev_collab_k` 的 `schedule_inf` + `v3_greedy` 的区间预筛）、`week05_truck_drone_v2.py`、`fstsp_mc.py`、`drone_scheduling.py`
- 第三轮回归测试：`tests/test_evaluators.py::test_v3_rejects_overlapping_sorties`、`::test_v3_greedy_produces_a_feasible_schedule`；W5 与 M&C 评估器的回归测试在 `tests/test_truck_drone.py`（`::test_v2_rejects_sortie_that_launches_while_drone_is_airborne`、`::test_v2_truck_waits_for_a_late_drone`、`::test_mc_rejects_sortie_that_launches_while_drone_is_airborne`、`::test_mc_evaluator_matches_shared_fstsp_evaluator_on_random_plans`、`::test_depot_only_baseline_agrees_across_week05_scripts`）
- 失败案例：`docs/reference/failure_cases_master.md` 的 FC-7-5
- 第三轮重跑的日志与 CSV：`src/results/v3_ev_collab_*`、`v3_ablation_*`、`week05_truck_drone_v2_output.txt`
