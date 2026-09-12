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

脚本会按依赖顺序跑完所有 headline 实验，逐个打印 `OK / FAIL` 与耗时。GA 基线最慢，整轮约 40–60 分钟。也可以单独跑任意一个脚本，例如：

```bash
python src/experiments/week06_sensitivity.py
```

每个脚本都通过 `__file__` 三级 `dirname` 解析仓库根，所以从任何目录运行都可以。

## 2b. 运行回归测试

`tests/` 下是用 pytest 写的回归测试，覆盖模型的关键不变量：K=1 无人机评估器等于单架、更多无人机不会更差、V3 解服务到每一位顾客、调度恒有 `greedy ≥ local ≥ optimal` 且下界合法、消融的 `abl_cap1` 精确复现已发表基线。约 1 秒跑完：

```bash
python -m pytest tests/ -q
```

每个实验脚本在日志头部打印运行机硬件（CPU / 核数 / 内存 / 平台），并在 raw CSV 中记录 `runtime_s`（`week08_lns_raw.csv`、`week08_multidrone_std_raw.csv`、`v3_ev_collab_raw.csv`、`week08_mc_benchmark_raw.csv` 等）。

## 3. 每条结论 → 脚本 → 产物 对照

| 报告中的结论 | 脚本 | 种子 / 参数 | 主要产物 |
|---|---|---|---|
| 三基线 vs BKS（PyVRP −3.0% / OR-Tools +7.2% / GA +36.6%±15.8%） | `benchmark_official_solomon.py` + `baseline_pyvrp_vrptw.py` + `baseline_ga_vrptw.py` → `baseline_consolidated.py` | GA 5 种子；OR-Tools / PyVRP 决定性 | `src/results/baseline_consolidated.csv`、`figures/baseline_gap_by_family.png` |
| 参数敏感性（电池 / 续航 / 每架次 / 规模） | `week06_sensitivity.py` | 5 种子；n=12 | `src/results/week06_sensitivity.csv`、`figures/sensitivity_panels.png` |
| 多目标权衡（距离 −32% / 时长 −34%，两轴占优） | `week06_multi_objective.py` | 5 权重 × 5 种子 | `src/results/week06_multi_objective.csv`、`figures/mo_*.png` |
| 受控消融（多顾客能力为主增益 +8.6~12.1pp；sanity check 通过） | `week07_improvement_ablation.py` | 40 算例 | `src/results/week07_ablation_summary.csv` |
| FSTSP 复现（V2 比 M&C 2015 短 10.2–14.2%） | `week07_fstsp_repro.py` | 40 算例 | `src/results/week07_fstsp_*.csv` |
| 规模衰减（N=50 收益 3.4%、单机调度拒绝 101 万） | `week06_largeN.py` | 5 种子 | `src/results/week06_largeN_summary.csv` |
| LNS 改进（相对贪心 +12.5~21.3%，缓冲规模衰减） | `week08_lns.py` | 60 算例（10 种子 × N=8/12/16/20/30/50）；确定性 | `src/results/week08_lns_summary.csv`、`figures/lns_vs_greedy.png` |
| 多无人机（K=1/2/3；K=1→3 时 N=50 收益 29.5%→38.1%） | `week08_multidrone.py` | 同 60 算例 × K=1/2/3；确定性 | `src/results/week08_multidrone_summary.csv`、`figures/multidrone.png` |
| 标准算例 + K=1/2/3/5 + 最优调度 | `week08_multidrone_std.py`（+ `fstsp_instances.py`、`drone_scheduling.py`） | 16 个 Solomon 标准实例；确定性 | `src/results/week08_multidrone_std_summary.csv`、`week08_scheduling.csv`、`figures/multidrone_std.png` |
| 论文原始算例（M&C 2015；c1K1 的 LNS/OFV=0.901） | `week08_mc_benchmark.py` + `fstsp_mc.py` | 36 个原始 10 顾客实例；确定性 | `src/results/week08_mc_benchmark_raw.csv` |
| V3（电动卡车+无人机+充电+时间窗；相对纯电卡车 K=1 降 34.7%~53.4%、K=3 达 72.8%） | `v3_ev_collab.py` | 4 规模 × 10 种子 × K=1/2/3；确定性 | `src/results/v3_ev_collab_summary.csv`、`v3_ev_collab_raw.csv` |
| 精确最优性 gap（CP-SAT 求小规模精确最优，对照我的贪心/LNS） | `week08_exact_gap.py` + `cpsat_fstsp.py` | n=8/10/12 × 5 种子；CP-SAT 上限 180s | `src/results/week08_exact_gap_raw.csv` / `_summary.csv` |
| 配对显著性检验（Wilcoxon 符号秩） | `stat_tests.py` | 读 W6/W7/W8 的 CSV；numpy 手写、无新依赖 | `src/results/stat_tests.csv` |

## 4. 说明与边界

- **CSV 按 `.gitignore` 设计不入库**：结果靠脚本 + 种子本地重跑生成；仓库保留的是脚本、日志（`.txt` / `.log`）与图（PNG）。
- **硬件**：Windows 11 / Python 3.13.14 / OR-Tools 9.15.6755 / Intel 20 逻辑核 / 32GB 内存（每个实验日志头部也会打印实测值；环境细节见 `docs/env_record.md`）。
- **续航 R 敏感性**在 2026-09-10 修复过一个 bug（之前 `mk_range` 未把续航传给模型，扫描恒为 50.5%）；修复后曲线见上方 §2。
- **多目标为粗前沿**：加权和贪心，不是完整 NSGA-II / Pareto 求解器（见 `docs/experiment_evidence_index_zh.md` §3）。
