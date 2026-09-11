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

## 3. 每条结论 → 脚本 → 产物 对照

| 报告中的结论 | 脚本 | 种子 / 参数 | 主要产物 |
|---|---|---|---|
| 三基线 vs BKS（PyVRP −3.0% / OR-Tools +7.2% / GA +36.6%±15.8%） | `benchmark_official_solomon.py` + `baseline_pyvrp_vrptw.py` + `baseline_ga_vrptw.py` → `baseline_consolidated.py` | GA 5 种子；OR-Tools / PyVRP 决定性 | `src/results/baseline_consolidated.csv`、`figures/baseline_gap_by_family.png` |
| 参数敏感性（电池 / 续航 / 每架次 / 规模） | `week06_sensitivity.py` | 5 种子；n=12 | `src/results/week06_sensitivity.csv`、`figures/sensitivity_panels.png` |
| 多目标权衡（距离 −56% / 时长 −33%，两轴占优） | `week06_multi_objective.py` | 5 权重 × 5 种子 | `src/results/week06_multi_objective.csv`、`figures/mo_*.png` |
| 受控消融（多顾客能力为主增益 +6.6~17.7pp；sanity check 通过） | `week07_improvement_ablation.py` | 40 算例 | `src/results/week07_ablation_summary.csv` |
| FSTSP 复现（V2 比 M&C 2015 短 8–22%，卸载约 2 倍） | `week07_fstsp_repro.py` | 40 算例 | `src/results/week07_fstsp_*.csv` |
| 规模衰减（N=50 收益 12.1%、会合否决 453 万） | `week06_largeN.py` | 5 种子 | `src/results/week06_largeN_summary.csv` |

## 4. 诚实说明

- **CSV 按 `.gitignore` 设计不入库**：结果靠脚本 + 种子本地重跑生成；仓库保留的是脚本、日志（`.txt` / `.log`）与图（PNG），因此老师看到的是"可重跑的证据链"而非孤数。
- **硬件**：Windows / Python 3.13.14 / OR-Tools 9.15.6755 / 20 核（详见 `docs/env_record.md`）。
- **续航 R 敏感性**在 2026-09-10 修复过一个 bug（之前 `mk_range` 未把续航传给模型，扫描恒为 50.5%）；修复后曲线见上方 §2。
- **多目标为粗前沿**：加权和贪心，不是完整 NSGA-II / Pareto 求解器（见 `docs/experiment_evidence_index_zh.md` §7）。
