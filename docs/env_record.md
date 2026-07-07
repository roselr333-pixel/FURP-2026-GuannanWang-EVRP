# Environment Record（环境记录）

> 满足 Week 1 Lab Step 2 与 Week 1 Checkpoint 的 "Environment" 要求。
> 复现用：在**任意干净机器**上按下面步骤即可跑通全部基线。

## 1. 系统与硬件
- **操作系统**：Windows 11 (64-bit)
- **CPU**：20 核（本机逻辑核数，记录于 `week03_experiment_log.txt` 的 Hardware 行）
- **内存**：本机默认；OR-Tools 小规模算例内存占用 < 200 MB

## 2. 软件版本（已固定，保证可复现）
- **Python**：3.13.14（使用 WorkBuddy 管理的隔离解释器，避免污染系统 Python）
- **包管理器**：`venv` + `pip`
- **主要依赖**：
  - `ortools==9.15.6755` —— 求解器（VRP / VRPTW / EVRP-TW 基线）
  - `numpy>=1.26`、`pandas>=2.0` —— 数据处理
  - `matplotlib>=3.7` —— 路线可视化（PNG 图）

## 3. 安装命令（精确、可复制）
```bash
# 1) 用 Python 3.13 创建隔离虚拟环境
python -m venv venv
# Windows 激活：
venv\Scripts\activate

# 2) 安装固定版本依赖
pip install -r src/requirements.txt
# （requirements.txt 含：ortools==9.15.6755, numpy>=1.26, pandas>=2.0, matplotlib>=3.7）
```

## 4. 运行命令（各周实验）
```bash
# Week 1 冒烟测试（含路线 PNG）
python src/experiments/week01_baseline.py

# Week 3 标准算例复现
python src/experiments/week03_reproduce.py

# Week 3 多规模公平对比实验（汇总表 + CSV + 路线图）
python src/experiments/week03_experiment.py

# Week 4 EVRP-TW（电池 + 充电站 + 电量违约表）
python src/experiments/week04_evrp_tw.py

# Week 5 卡车+无人机协同基线
python src/experiments/week05_truck_drone.py
```

## 5. 求解器参数（记录于输出文件）
- 初解策略：`PATH_CHEAPEST_ARC`
- 改进策略（"improved" 方法）：`GUIDED_LOCAL_SEARCH`（Week 3 用 4s 预算；Week 1 用 3s 预算）
- 自定义 2-opt 后处理：仅接受更短且满足时间窗的翻转（见 `week03_experiment.py` 的 `two_opt`）
- 随机种子：Week 3 用 `seed = 7 + size`（10→17, 20→27, 40→47）；OR-Tools 给定种子后结果确定

## 6. 复现注意事项
- 所有结果文件写入 `src/results/`，均为脚本自动生成，可删除后重跑得到一致结果。
- 路由图使用**环形布局**（因 Week 1 用距离矩阵、无坐标），仅用于展示访问顺序，不代表真实地理位置。
