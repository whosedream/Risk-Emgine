# CLAUDE.md — 智能风控引擎 · 特征提取与风险打分

**Version:** 1.2.0 | **Last updated:** 2026-06-23
**项目：** 智能金融平台-模拟风控引擎 | **GitHub：** https://github.com/xiangu152/Risk-Emgine
**北理工智能风控系统 — 结课作业**

> **变更契约：** API 契约（特征键名、值域、函数签名）变更需同步更新版本号与日期。破坏性变更需通知所有组员。

---

## 项目背景

本项目从多维行为日志中提取欺诈特征并生成风险评分。整体 pipeline：

```
数据生成(@廖文远) → 特征提取(我) → 风险打分(我) → 等级划分 → 可视化
```

**我的职责范围：**
- 特征提取（`feature_extraction.py`）：从 CSV 行为日志计算 17 维欺诈特征
- 风险打分模型（`scoring_model.py`）：规则引擎 + ML 混合评分，输出 0~100 风险分
- 模型训练（`train_ml_model.py`）：RandomForest / GradientBoosting

**不负责：** 数据模拟生成（@廖文远）、可视化展示、前后端开发（其他组员负责）。

**数据生成约定：** 数据模块输入参数 `start_date, end_date, output_dir, mode, num_accounts`；输出 `${start_date}_${end_date}_risk.csv`。`mode=train` 含 `label` 列（0/1/2），`mode=test` 无标签。数据基于角色故事生成，保证同账户行为逻辑一致。

**当前数据：** `@data: data/20260601_20260630_risk.csv` — 10,098 行 / 100 账户 / 30 天，按账户 70/15/15 分层划分至 `data/splits/`。

### 全局偏好

全局偏好继承自 `~/.claude/CLAUDE.md`，关键约定推广至本项目：
- **用户指令：** 成熟的追求前沿技术的 AI Agent/全栈开发工程师，优先中文，uv 管理 Python 依赖，TDD+SDD 开发。

---

## API 契约 — extract_features()

组员主要集成入口。输出 dict 可直接传入 `score_risk()` 或 `score_risk_hybrid()`。

```python
def extract_features(csv_path: str) -> dict[str, float]:
    """从行为日志 CSV 提取欺诈特征向量。

    Returns 17 个特征（v1.2.0），向后兼容旧 7 特征输入。

    Raises:
        ValueError: CSV 无法读取、为空、或缺少必填字段时抛出。
    """
```

**返回 dict 结构（共 17 个特征键，v1.2.0）：**

### 基础特征（7 个，v1.0~v1.1）

| 键名 | 类型 | 值域 | 含义 |
|------|------|------|------|
| `device_reuse_ratio` | float | 0.0~1.0 | 设备复用率（基于 `machine` 正则提取设备指纹） |
| `ip_change_freq` | float | 0.0~1.0 | IP 变更频率（归一化） |
| `tx_freq` | float | >=0.0 | 交易频率（原始计数） |
| `login_fail_ratio` | float | 0.0~1.0 | 登录失败率（从 `behavior_type` 挖掘） |
| `amount_anomaly_score` | float | 0.0~1.0 | 金额异常分数（MAD 稳健 Z-score） |
| `behavior_time_anomaly` | float | 0.0~1.0 | 行为耗时异常（`behavior_period_time < 5s` 占比） |
| `multi_region_risk` | float | 0.0/1.0 | 多地区风险 |

### 滑动窗口速度特征（4 个，v1.2.0）

| 键名 | 类型 | 值域 | 含义 |
|------|------|------|------|
| `tx_velocity_5min` | float | >=0.0 | 5 分钟窗口内最多交易数 |
| `tx_velocity_1h` | float | >=0.0 | 1 小时窗口内最多交易数 |
| `device_switch_24h` | float | >=0.0 | 24h 窗口内最多不同设备数 |
| `ip_switch_24h` | float | >=0.0 | 24h 窗口内最多不同 IP 数 |

### 交易间隔 + 金额基线特征（4 个，v1.2.0）

| 键名 | 类型 | 值域 | 含义 |
|------|------|------|------|
| `tx_interval_mean_sec` | float | >=0.0 | 平均交易间隔（秒），越低越可疑 |
| `tx_burst_ratio` | float | 0.0~1.0 | 60 秒内连续交易占比 |
| `amount_user_deviation` | float | >=0.0 | 用户均值偏离全局中位数的 Z-score |
| `amount_user_max_ratio` | float | >=0.0 | 最大单笔交易 / 用户均值 |

### 时间循环特征（2 个，v1.2.0）

| 键名 | 类型 | 值域 | 含义 |
|------|------|------|------|
| `night_tx_ratio` | float | 0.0~1.0 | 凌晨 1am-5am 交易占比 |
| `odd_hour_tx_ratio` | float | 0.0~1.0 | 非工作时间 (0-6am + 10pm-12am) 交易占比 |

**JSON 输出示例（v1.2.0，17 特征）：**

```json
{
  "device_reuse_ratio": 0.01, "ip_change_freq": 0.01, "tx_freq": 27.0,
  "login_fail_ratio": 0.001, "amount_anomaly_score": 0.40,
  "behavior_time_anomaly": 0.06, "multi_region_risk": 0.0,
  "tx_velocity_5min": 1.7, "tx_velocity_1h": 2.9,
  "device_switch_24h": 1.0, "ip_switch_24h": 8.5,
  "tx_interval_mean_sec": 43200.0, "tx_burst_ratio": 0.05,
  "amount_user_deviation": 1.2, "amount_user_max_ratio": 3.5,
  "night_tx_ratio": 0.09, "odd_hour_tx_ratio": 0.21
}
```

**异常（ValueError）：**
| 触发条件 | 错误信息示例 |
|----------|-------------|
| CSV 文件无法读取 | `无法读取CSV文件: bad/path.csv` |
| CSV 为空或无数据行 | `CSV文件为空或无数据行: data/empty.csv` |
| 缺少必填字段 | `CSV缺少必填字段: {'account_id', 'machine'}` |
| 无有效用户 | `CSV数据中无有效用户` |
> 警告：返回 dict 的键名和值域变更属于**破坏性变更**，需同步更新版本号并通知所有组员。

---

## API 契约 — extract_features_per_user()

```python
def extract_features_per_user(csv_path: str) -> dict[str, dict[str, float]]:
    """返回 {user_id: {feature_name: value}}，每个用户独立评分。

    Raises:
        ValueError: CSV 无法读取、为空、或缺少必填字段时抛出。
    """
```

- 与 `extract_features()` 共享 `_load_and_validate()` 完成 CSV 读取/校验/时间戳解析
- `extract_features()` 对所有用户取均值（聚合模式），内部复用 `extract_features_per_user()`
- 每个用户独立计算全部 17 特征

---

## CSV 数据格式

> ⚠️ **约定草案** — 字段需与 @廖文远 的数据生成模块对齐。`label` 字段仅训练模式存在。

输入文件：`{start_date}_{end_date}_risk.csv`（由数据生成模块产出）。

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | `account_id` | str | 账户唯一标识 |
| 2 | `account_name` | str | 账户名称 |
| 3 | `region` | str | 地区 |
| 4 | `pub_time` | datetime | 行为发生时间（混合时区格式，代码兼容） |
| 5 | `ip_address` | str | IP 地址 |
| 6 | `type` | str | 行为类型：`login` / `register` / `transaction` / `browse` 等 13 种 |
| 7 | `machine` | str | 设备标识（自然语言，正则提取设备指纹） |
| 8 | `behavior_type` | str | 行为细分类型 |
| 9 | `behavior_period_time` | float | 行为持续时间（秒） |
| 10 | `behavior_log` | str | 行为日志描述 |
| 11 | `money_size` | float | 交易金额 |
| 12 | `sign_up_time` | datetime | 账户注册时间 |
| 13 | `label` | int | 风险标签（仅训练模式）：0=低/1=中/2=高 |

**当前数据特性：** 基于角色故事生成，100 账户，每账户约 101 行事件。已知局限：
- 设备指纹无跨账户共享 → `device_reuse_ratio` ≈ 0
- 登录失败事件极少（2/2896）→ `login_fail_ratio` ≈ 0
- 所有账户单一地区 → `multi_region_risk` = 0
- 每账户固定设备 → `device_switch_24h` ≤ 1

---

## API 契约 — score_risk()

风险打分函数，接收特征向量，输出 0~100 风险评分。

```python
def score_risk(
    features: dict[str, float],
    weights: dict[str, float] | None = None,
) -> dict[str, float | str]:
    """加权求和 + 规则增强，计算综合风险评分"""
```

- **评分方法：** 加权求和（17 特征 × 权重）+ 规则增强（16 条，可叠加）
- **默认权重（v1.2.0，总和=1.0）：**

| 特征键名 | 权重 | 归一化方式 |
|----------|------|-----------|
| `device_reuse_ratio` | 0.10 | 原值 0~1 |
| `ip_change_freq` | 0.08 | 原值 0~1 |
| `tx_freq` | 0.08 | `min(1.0, tx_freq/100)` |
| `login_fail_ratio` | 0.08 | 原值 0~1 |
| `amount_anomaly_score` | 0.10 | 原值 0~1 |
| `behavior_time_anomaly` | 0.07 | 原值 0~1 |
| `multi_region_risk` | 0.05 | 原值 0/1 |
| `tx_velocity_5min` | 0.08 | `min(1.0, x/10)` |
| `tx_velocity_1h` | 0.08 | `min(1.0, x/30)` |
| `device_switch_24h` | 0.04 | `min(1.0, x/5)` |
| `ip_switch_24h` | 0.05 | `min(1.0, x/10)` |
| `tx_interval_mean_sec` | 0.04 | `1-min(1.0, x/3600)` (反向) |
| `tx_burst_ratio` | 0.04 | 原值 0~1 |
| `amount_user_deviation` | 0.03 | `min(1.0, x/5)` |
| `amount_user_max_ratio` | 0.03 | `min(1.0, x/10)` |
| `night_tx_ratio` | 0.03 | 原值 0~1 |
| `odd_hour_tx_ratio` | 0.02 | 原值 0~1 |

- **规则增强（16 条，v1.2.0）：**

| # | 触发条件 | 加分 | 欺诈模式 |
|---|---------|------|---------|
| 1 | `device_reuse > 0.9` 且 `tx_freq > 50` | +10 | 设备农场+高频交易 |
| 2 | `ip_change > 0.8` 且 `login_fail > 0.5` | +10 | IP 频繁变更+撞库 |
| 3 | `amount_anomaly > 0.7` | +15 | 金额极端异常 |
| 4 | `login_fail > 0.7` | +20 | 暴力破解 |
| 5 | `device_reuse > 0.2` | +19 | 设备共享 |
| 6 | `ip_change > 0.1` 且 `amount_anomaly > 0.3` | +15 | 账户盗用 |
| 7 | `device_reuse > 0.15` 且 `login_fail > 0.3` | +15 | 设备农场撞库 |
| 8 | `tx_freq > 10` 且 `amount_anomaly > 0.3` | +15 | 洗钱模式 |
| 9 | `behavior_time > 0.3` 且 `tx_freq > 20` | +15 | 自动化脚本跑量 |
| 10 | `multi_region > 0` | +12 | 多地区异常 |
| 11 | `tx_velocity_5min > 5` | +12 | 交易爆发 |
| 12 | `tx_velocity_1h > 15` 且 (设备或IP切换频繁) | +15 | 账户接管后快速变现 |
| 13 | `tx_interval_mean < 30s` 且 `tx_freq > 5` | +10 | 自动化脚本 |
| 14 | `amount_user_max_ratio > 10` | +10 | 单笔超大额 |
| 15 | `tx_burst > 0.5` 且 `tx_freq > 10` | +10 | 批量操作 |
| 16 | `night_tx > 0.3` | +8 | 凌晨异常 |

---

## API 契约 — score_risk_hybrid() [v1.2.0 NEW]

```python
def score_risk_hybrid(
    features: dict[str, float],
    weights: dict[str, float] | None = None,
    alpha: float = 1.0,
) -> dict[str, float | str]:
    """规则模型 + RandomForest 加权融合评分。

    最终分 = α × 规则分 + (1-α) × ML 概率分

    Returns: {"score", "level", "level_range", "rule_score", "ml_score"}
    """
```

- **依赖：** 需先运行 `train_ml_model.py` 生成 `data/model/scaler.pkl` + `data/model/random_forest.pkl`
- **alpha=1.0**（默认）：退化为纯规则模型，无需 ML 文件
- **alpha=0.2**：混合模式，当前在小样本上规则更优
- ML 模型使用 17 特征，内部自动标准化

---

### 内部 API — `_extract_features_per_user_from_df()`

供评估脚本使用的内部接口，避免重复 I/O：

```python
from feature_extraction import _extract_features_per_user_from_df, _load_and_validate

df, has_amount = _load_and_validate(csv_path)
per_user = _extract_features_per_user_from_df(df, has_amount)
# → dict[str, dict[str, float]]
```

### 统一评估 — `evaluate.py`

```bash
python evaluate.py full          # 全量数据评估
python evaluate.py splits        # train/val/test 三集合评估
python evaluate.py hybrid        # 规则 vs ML vs Hybrid α 扫参
python evaluate.py calibrate     # 阈值校准
python evaluate.py all --format json  # 全部 + JSON 报告输出
```

---

## 风险等级

| 等级 | 分值范围 | 等级标识 | 说明 |
|------|----------|---------|------|
| 低风险 | 0~30 | `"LOW"` | 行为正常，无需关注 |
| 中风险 | 31~55 | `"MEDIUM"` | 存在可疑模式，建议人工复核 |
| 高风险 | 56~100 | `"HIGH"` | 极可能欺诈，触发警报/拦截 |

> v1.2.0 校准：HIGH 门槛从 71→55（基于验证集 PR 曲线优化，Kappa 0.736→0.872）

---

## 版本与开发规范

### 版本管理

- **当前版本：** 1.2.0
- **语义化版本：** MAJOR.MINOR.PATCH
- **变更历史：**
  - **1.2.0 (2026-06-23):** 新增 10 个特征（速度/间隔/金额基线/时间循环，总计 17 维）；新增 6 条规则（#11~#16，总计 16 条）；引入 ML 混合评分 `score_risk_hybrid()`（RandomForest/GradientBoosting）；权重重新分配至 17 特征（总和 1.0）；新增依赖 scikit-learn/joblib/shap；数据按账户 70/15/15 分层划分；SHAP 特征贡献度分析
  - **1.1.0 (2026-06-23):** CSV 字段对齐真实数据规范（13 字段）；新增 2 个特征 `behavior_time_anomaly`、`multi_region_risk`；新增 2 条规则（#9、#10）；字段名映射 `user_id→account_id` 等
  - **1.0.1:** extract_features() 不再静默返回全零，改为抛出 ValueError
  - **1.0.0:** 初始版本，5 特征 + 8 规则

### 开发偏好

- **语言 & 工具链：** Python 3.10+，Pandas、NumPy、scikit-learn
- **依赖管理：** `uv`（`uv add pandas scikit-learn joblib shap --dev pytest`）
- **开发方式：** TDD + SDD（规范驱动，API 契约先行）
- **项目结构：**
  ```
  feature_extraction.py   — 特征提取（17 维）
  scoring_model.py         — 风险打分（规则引擎 + ML 混合）
  evaluate.py              — 统一评估入口（python evaluate.py full|splits|hybrid|calibrate|all）
  train_ml_model.py        — ML 模型训练
  shap_analysis.py         — SHAP 特征贡献度分析
  data_quality_report.py   — 数据质量全景分析
  calibrate_thresholds.py  — 阈值校准（独立脚本，也可通过 evaluate.py calibrate 调用）
  tests/                   — pytest 测试（43 cases）
  data/splits/             — train/val/test 划分文件
  data/model/              — 训练好的 ML 模型 + SHAP 图表
  data/evaluation/         — 评估报告输出（JSON/HTML）
  ```
- **类型注解：** 所有公共函数使用完整的 Python type hints
- **代码风格：** surgical changes（只改任务要求的部分），simplicity first

### 集成示例

```python
from feature_extraction import extract_features, extract_features_per_user
from scoring_model import score_risk, score_risk_hybrid

# 聚合模式
features = extract_features("data/20260601_20260630_risk.csv")
result = score_risk(features)
# → {"score": 64.8, "level": "HIGH", "level_range": "56~100"}

# Per-user 模式
per_user = extract_features_per_user("data/20260601_20260630_risk.csv")
for uid, feat in per_user.items():
    r = score_risk(feat)
    print(f"{uid}: {r['score']:.0f} {r['level']}")

# 混合模式（需先训练 ML 模型）
result = score_risk_hybrid(features, alpha=0.2)
# → {"score": 66.4, "level": "MEDIUM", "rule_score": 50.9, "ml_score": 70.3}
```

### 已知局限

| 特征 | 状态 | 原因 |
|------|------|------|
| `device_reuse_ratio` | RF 重要性 = 0 | 模拟数据中设备指纹无跨账户共享 |
| `login_fail_ratio` | RF 重要性 = 0 | behavior_type 中失败事件仅 2 次 |
| `multi_region_risk` | 恒为 0 | 角色故事保证单一地区 |
| `device_switch_24h` | 恒为 1 | 每账户固定设备 |
| ML 模型 | 小样本过拟合 | 训练集仅 69 账户，17 特征 > 最优饱和度 |
