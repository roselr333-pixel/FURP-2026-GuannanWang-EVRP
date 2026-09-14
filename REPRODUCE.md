# 如何复现（Reproduce）

本仓库所有实验都可以用一条命令重跑。环境：Python 3.13 虚拟环境（Windows）；依赖见根目录 `requirements.txt`。

## 1. 安装依赖

```bash
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt
```

> `pyvrp` 是 PyVRP 基线（`baseline_pyvrp_vrptw.py`）专用；其余实验只需 `ortools`。

## 2. 一键重跑所有实验

```bash
python run_all.py
```

脚本会按依赖顺序跑完仓库里的全部实验（headline + W1–W5）与 `figures/` 下的全部图：实验先跑，绘图工具最后跑（它们读实验写出的 CSV）。逐个打印 `OK / FAIL` 与耗时。GA 基线最慢（本机单跑约 70–90 分钟），整轮约 1.5–2 小时。也可以单独跑任意一个脚本，例如：

```bash
python src/experiments/week06_sensitivity.py
```

每个脚本都通过 `__file__` 三级 `dirname` 解析仓库根，所以从任何目录运行都可以。

## 2b. 运行回归测试

`tests/` 下是用 pytest 写的回归测试，覆盖模型的关键不变量：K=1 无人机评估器等于单架、更多无人机不会更差、V3 解服务到每一位顾客、调度恒有 `greedy ≥ local ≥ optimal` 且下界合法、消融的 `abl_cap1` 精确复现已发表基线、W5/M&C 评估器的物理性与跨模块一致性。本机约 35 秒跑完（167 个用例，其中 `tests/test_cpsat_exact.py` 的 CP-SAT 校验占大头）：

```bash
python -m pytest tests/ -q
```

每个实验脚本在日志头部打印运行机硬件（CPU / 核数 / 内存 / 平台），并在 raw CSV 中记录 `runtime_s`（`week08_lns_raw.csv`、`week08_multidrone_std_raw.csv`、`v3_ev_collab_raw.csv`、`week08_mc_benchmark_raw.csv` 等）。

## 3. 每条结论 → 脚本 → 产物 对照

| 报告中的结论 | 脚本 | 种子 / 参数 | 主要产物 |
|---|---|---|---|
| 三基线 vs BKS（PyVRP −3.0% / OR-Tools +7.2% / GA +36.6%±15.8%） | `benchmark_official_solomon.py` + `baseline_pyvrp_vrptw.py` + `baseline_ga_vrptw.py` → `baseline_consolidated.py` | GA 5 种子；PyVRP 固定 seed；OR-Tools 10 s 时间预算（均值 gap 逐次 7.2%~8.1%） | `src/results/baseline_consolidated.csv`、`figures/baseline_consolidated.png` |
| 参数敏感性（电池 / 续航 / 每架次 / 规模） | `week06_sensitivity.py` | 5 种子；n=12 | `src/results/week06_sensitivity.csv`、`figures/sensitivity_panels.png` |
| 多目标权衡（距离 −32% / 时长 −34%，两轴占优） | `week06_multi_objective.py` | 5 权重 × 5 种子 | `src/results/week06_multi_objective.csv`、`figures/mo_*.png` |
| 受控消融（多顾客能力为主增益 +8.6~12.1pp；sanity check 通过） | `week07_improvement_ablation.py` | 40 算例 | `src/results/week07_ablation_summary.csv` |
| 核心消融搬到标准算例（多顾客能力 +7.2~8.9pp，与合成一致） | `week07_ablation_std.py`（+ `fstsp_instances.py`） | 48 个标准实例；确定性 | `src/results/week07_ablation_std_summary.csv`、`figures/ablation_std.png` |
| V3（电动+时间窗）上的核心消融（多顾客 +8.5~12.5pp 是主增益；N=20 转为 −2.8pp） | `v3_ablation.py`（+ `v3_ev_collab.py`） | 40 算例（10 种子 × N=8/12/16/20） | `src/results/v3_ablation_summary.csv`、`figures/v3_ablation.png` |
| 无人机能耗/载荷闸门装到主线（V3 K=1 收益 33.5~53.0%、K=3 达 72.4%；代价是 1.5~8.1% 的 makespan；N≥16 时 K=1→3 的边际价值少 5~10pp，返回的计划全部可行） | `drone_energy_mainline.py`（+ `drone_energy.py`） | 4 规模 × 10 种子 × K=1/2/3 × BETA ∈ {0, 0.02}；确定性 | `src/results/drone_energy_mainline_raw.csv` / `_summary.csv`、`figures/drone_energy_mainline.png` |
| 无人机能耗/载荷模型下的消融（多顾客增益 +10.4→+6.1pp；不感知能耗的基线计划大量不可行） | `drone_energy_ablation.py`（+ `drone_energy.py`） | 88 实例 × BETA ∈ {0, 0.02, 0.04} | `src/results/drone_energy_summary.csv`、`figures/drone_energy.png` |
| FSTSP 复现（V2 比 M&C 2015 短 10.2–14.2%） | `week07_fstsp_repro.py` | 40 算例 | `src/results/week07_fstsp_*.csv` |
| 规模衰减（N=50 收益 3.4%、单机调度拒绝 101 万） | `week06_largeN.py` | 5 种子 | `src/results/week06_largeN_summary.csv` |
| LNS 改进（相对贪心 +12.5~21.3%，缓冲规模衰减） | `week08_lns.py` | 60 算例（10 种子 × N=8/12/16/20/30/50）；确定性 | `src/results/week08_lns_summary.csv`、`figures/lns_vs_greedy.png` |
| ALNS 在物理 FSTSP 模型上比原 LNS 再短 2.7~12.2%（平均 +6.3%）；自适应权重不划算（冻结权重在 n=8/12/16 上一样好甚至更好） | `alns_fstsp.py`（+ `cpsat_fstsp.py`） | 5 规模 × 5 种子；迭代 = 100 × N，销毁规模 max(2, 0.35N)；确定性 | `src/results/week08_alns_raw.csv` / `_summary.csv`、`figures/alns_fstsp.png` |
| 多无人机（K=1/2/3；K=1→3 时 N=50 收益 29.5%→38.1%） | `week08_multidrone.py` | 同 60 算例 × K=1/2/3；确定性 | `src/results/week08_multidrone_summary.csv`、`figures/multidrone.png` |
| 标准算例 + K=1/2/3/5 + 最优调度 | `week08_multidrone_std.py`（+ `fstsp_instances.py`、`drone_scheduling.py`） | 16 个 Solomon 标准实例；确定性 | `src/results/week08_multidrone_std_summary.csv`、`week08_scheduling.csv`、`figures/multidrone_std.png` |
| 论文原始算例（M&C 2015；c1K1 的 LNS/OFV=0.924） | `week08_mc_benchmark.py` + `fstsp_mc.py` | 36 个原始 10 顾客实例；确定性 | `src/results/week08_mc_benchmark_raw.csv` |
| V3（电动卡车+无人机+充电+时间窗；相对纯电卡车 K=1 降 33.5%~52.4%、K=3 达 72.5%） | `v3_ev_collab.py` | 4 规模 × 10 种子 × K=1/2/3；确定性 | `src/results/v3_ev_collab_summary.csv`、`v3_ev_collab_raw.csv` |
| 精确最优性 gap 与证明边界（CP-SAT 热启动，对照我的贪心/LNS；n=8 证明最优，n≥10 只能给可行计划而认证下界为 0） | `week08_exact_gap.py` + `cpsat_fstsp.py` | n=8/10/12/14/16 × 5 种子；每实例 120/60 s | `src/results/week08_exact_gap_raw.csv` / `_summary.csv` |
| 配对显著性检验（Wilcoxon 符号秩） | `stat_tests.py` | 读 W6/W7/W8 的 CSV；numpy 手写、无新依赖 | `src/results/stat_tests.csv` |
| 同一模型跑标准算例（Schneider 2014 原始数据） | `week06_standard_instances.py` + `std_evrp_instances.py` | 6 族 × 4 个子集 × N=8/12/16/20；两种载重口径 | `src/results/week06_std_evrp_summary.csv`、`figures/std_instances.png` |
| 卡车载重是否 binding（CAP=1000 已启用） | `week06_capacity_study.py` | 7 个规模 × 5 种子 × cap ∈ {1000, 600, 400} | `src/results/week06_capacity_summary.csv`、`figures/capacity_binding.png` |

## 3b. 图（`figures/`）→ 生成脚本

`figures/` 下的每张图都是 `run_all.py` 的一步，也可以单独重跑（只要对应的实验 CSV 已存在，单独跑绘图脚本即可，例如 `python src/tools/plot_lns.py`）：

| 图 | 回答什么问题 | 生成脚本 | 依赖的 CSV |
|---|---|---|---|
| `baseline_consolidated.png` | 三条基线在同一批 56 个 Solomon 实例上各差 BKS 多少 | `baseline_consolidated.py` | 三个基线结果 CSV |
| `pyvrp_family_gap.png` | PyVRP 是否在每个 family 都优于 BKS | `baseline_pyvrp_vrptw.py` | `baseline_pyvrp_vrptw_results.csv` |
| `sensitivity_panels.png` | 哪个设计变量对协同收益影响最大 | `week06_sensitivity.py` | `week06_sensitivity.csv` |
| `mo_scatter.png` / `mo_tradeoff.png` | 距离与完工时间之间是否存在权衡 | `week06_multi_objective.py` | `week06_multi_objective.csv` |
| `largen_scale_decay.png` | 规模大到什么程度协同不再划算 | `src/tools/gen_largen_figure.py` | `week06_largeN_summary.csv` |
| `ablation_std.png` | 核心消融在标准算例上是否成立 | `src/tools/gen_ablation_std_figure.py` | `week07_ablation_std_summary.csv` |
| `v3_ablation.png` | 电动 + 时间窗下增益来自哪一项 | `src/tools/gen_v3_ablation_figure.py` | `v3_ablation_summary.csv` |
| `drone_energy.png` | 加入能耗/载荷模型后结论怎么变 | `src/tools/gen_drone_energy_figure.py` | `drone_energy_summary.csv` |
| `drone_energy_mainline.png` | 把闸门开到 V3 与多无人机主线上，结论是否还成立 | `src/tools/gen_drone_energy_mainline_figure.py` | `drone_energy_mainline_summary.csv` |
| `lns_vs_greedy.png` | 改进阶段（LNS）是否值得 | `src/tools/plot_lns.py` | `week08_lns_summary.csv` |
| `alns_fstsp.png` | 搜索一侧还剩多少空间、自适应权重是否起作用 | `src/tools/gen_alns_figure.py` | `week08_alns_summary.csv` |
| `multidrone.png` | 多无人机（合成算例）的收益 | `src/tools/plot_multidrone.py` | `week08_multidrone_summary.csv` |
| `multidrone_std.png` | 标准算例 + 调度器的结果 | `src/tools/plot_multidrone_std.py` | `week08_multidrone_std_summary.csv`、`week08_scheduling.csv` |
| `exact_gap.png` | 启发式离精确最优有多远、证明在哪里停住（primal vs dual） | `src/tools/plot_exact_gap.py` | `week08_exact_gap_summary.csv`、`week08_exact_gap_raw.csv` |
| `std_instances.png` | 合成结论能否外推到标准算例 | `src/tools/gen_std_instances_figure.py` | `week06_std_evrp_summary.csv` |
| `capacity_binding.png` | 声明的卡车载重是否 binding | `src/tools/gen_capacity_figure.py` | `week06_capacity_summary.csv` |
| `schneider_routes.png` / `schneider_vehcomp.png` | 与 Schneider (2014) 的差距 | `src/tools/plot_schneider_routes.py` | `schneider_evrptw_bks_comparison.csv` |
| `src/results/week01_routes.png` | W1 冒烟测试的路线 | `week01_baseline.py` | — |
| `src/results/week03_route_n20_vrptw_improved.png` | W3 公平对比里 2-opt 的路线 | `week03_experiment.py` | — |

## 4. 说明与边界

- **CSV 按 `.gitignore` 设计不入库**：结果靠脚本 + 种子本地重跑生成；仓库保留的是脚本、日志（`.txt` / `.log`）与图（PNG）。`src/results/` 下的日志都由脚本自己写出：`baseline_ga_vrptw.py` 写 `baseline_ga_vrptw_output.txt` 与 `baseline_ga_multi_seed.log`（单种子对照用 `GA_SEEDS=20260717`，写 `baseline_ga_run.log` 与 `*_single_seed.*`），`baseline_pyvrp_vrptw.py` 写 `baseline_pyvrp_run.log`；逐文件对照见 `docs/reference/configs_and_parameters.md` §6。
- **硬件**：Windows 11 / Python 3.13.14 / OR-Tools 9.15.6755 / Intel 20 逻辑核 / 32GB 内存（每个实验日志头部也会打印实测值；环境细节见 `docs/reference/env_record.md`）。
- **续航 R 敏感性**在 2026-09-10 修复过一个 bug（之前 `mk_range` 未把续航传给模型，扫描恒为 50.5%）；修复后曲线见上方 §2。
- **多目标为粗前沿**：加权和贪心，不是完整 NSGA-II / Pareto 求解器（见 `docs/reference/experiment_evidence_index_zh.md` §3）。
