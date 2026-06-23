# 风控引擎 API 使用手册

> **版本 v1.2.0** | 特征提取 + 风险打分模块  
> 给前后端组员的集成参考

## 环境

```bash
# 安装依赖（仅首次）
uv sync

# 运行测试
uv run pytest tests/ -v
```

| 项目 | 说明 |
|------|------|
| Python | ≥3.12 |
| 依赖管理 | `uv`（`pip install uv` 安装） |
| 依赖声明 | `pyproject.toml` |

---

## 依赖

在 `pyproject.toml` 中声明，`uv sync` 自动安装：

```
numpy, pandas, scikit-learn, joblib, shap, xgboost
```

---

## 快速开始

```python
from feature_extraction import extract_features, extract_features_per_user
from scoring_model import score_risk, score_risk_hybrid

# 1. 特征提取（传入 CSV 路径，返回 17 维特征向量）
features = extract_features("data/20260601_20260630_risk.csv")

# 2. 风险打分（0~100）
result = score_risk(features)
# → {"score": 64.8, "level": "HIGH", "level_range": "56~100"}

# 3. 可选：ML 混合模式（需先运行 train_ml_model.py）
result = score_risk_hybrid(features)
```

---

## API 详解

### 特征提取 `extract_features()`

```python
def extract_features(csv_path: str) -> dict[str, float]:
```

**输入：** CSV 文件路径（13 字段，由 @廖文远 的数据模块生成）

**输出：** 17 个特征键值对

| 特征键 | 类型 | 值域 | 含义 |
|--------|------|------|------|
| `device_reuse_ratio` | float | 0~1 | 设备复用率 |
| `ip_change_freq` | float | 0~1 | IP 变更频率 |
| `tx_freq` | float | ≥0 | 交易次数 |
| `login_fail_ratio` | float | 0~1 | 登录失败率 |
| `amount_anomaly_score` | float | 0~1 | 金额异常（MAD Z-score） |
| `behavior_time_anomaly` | float | 0~1 | 行为耗时异常（<5s 占比） |
| `multi_region_risk` | float | 0/1 | 多地区风险 |
| `tx_velocity_5min` | float | ≥0 | 5 分钟窗口最大交易数 |
| `tx_velocity_1h` | float | ≥0 | 1 小时窗口最大交易数 |
| `device_switch_24h` | float | ≥0 | 24h 窗口最大不同设备数 |
| `ip_switch_24h` | float | ≥0 | 24h 窗口最大不同 IP 数 |
| `tx_interval_mean_sec` | float | ≥0 | 平均交易间隔（秒） |
| `tx_burst_ratio` | float | 0~1 | 60s 内连续交易占比 |
| `amount_user_deviation` | float | ≥0 | 用户均值偏离全局中位数的 Z-score |
| `amount_user_max_ratio` | float | ≥0 | 最大单笔 / 用户均值 |
| `night_tx_ratio` | float | 0~1 | 凌晨 1am-5am 交易占比 |
| `odd_hour_tx_ratio` | float | 0~1 | 非工作时间交易占比 |

**异常：** CSV 读取失败/字段缺失时抛出 `ValueError`

### Per-User 模式

```python
def extract_features_per_user(csv_path: str) -> dict[str, dict[str, float]]:
# → {"ACC_00001": {特征...}, "ACC_00002": {特征...}, ...}
```

每个账户独立提取特征，不会被其他账户稀释。

### 风险打分 `score_risk()`

```python
def score_risk(
    features: dict[str, float],
    weights: dict[str, float] | None = None,
) -> dict[str, float | str]:
```

**返回结构：**
```json
{"score": 64.8, "level": "HIGH", "level_range": "56~100"}
```

**风险等级：**

| 等级 | 分数 | level 值 | 建议动作 |
|------|------|----------|---------|
| 低风险 | 0~30 | `"LOW"` | 放行 |
| 中风险 | 31~55 | `"MEDIUM"` | 人工复核 |
| 高风险 | 56~100 | `"HIGH"` | 拦截/告警 |

### ML 混合评分 `score_risk_hybrid()`

```python
def score_risk_hybrid(
    features: dict[str, float],
    alpha: float = 0.2,
) -> dict[str, float | str]:
# → {"score": 66.4, "level": "HIGH", "rule_score": 50.9, "ml_score": 70.3}
```

使用 Voting Ensemble（RF + XGBoost + GBDT）与规则模型加权融合。  
需先运行 `python train_ml_model.py` 生成模型文件。

---

## 集成示例

### 后端：批量打分

```python
# 一键打分所有账户
per_user = extract_features_per_user("input.csv")
results = []
for uid, features in per_user.items():
    r = score_risk(features)
    results.append({
        "account_id": uid,
        "score": r["score"],
        "level": r["level"],
    })

# 高风险告警
high_risk = [r for r in results if r["level"] == "HIGH"]
print(f"高风险账户: {len(high_risk)}/{len(results)}")
```

### 前端：展示风险信息

```javascript
// API 返回示例
{
  "account_id": "ACC_00016",
  "score": 84.0,
  "level": "HIGH",
  "top_features": [
    {"name": "金额异常", "value": 1.0},
    {"name": "行为耗时异常", "value": 1.0},
    {"name": "交易频率", "value": 91.0}
  ]
}
```

---

## 准确率

测试集 15 账户（1,509 事件行），按账户 70/15/15 分层划分。

| 模型 | 准确率 | Kappa | 高风险检出 |
|------|--------|-------|-----------|
| 规则引擎 (16 条) | 60.0% | 0.182 | 0/1 |
| RandomForest | 73.3% | 0.492 | 0/1 |
| XGBoost | 80.0% | 0.545 | 0/1 |
| GradientBoosting | 80.0% | 0.545 | 0/1 |
| **Ensemble (RF+XGB+GBDT)** | **93.3%** | **0.873** | 0/1 |

| 指标 | 值 | 说明 |
|------|-----|------|
| Spearman r | **0.841** | 评分与真实风险排序高度一致 (p<0.001) |
| 低风险精确率 | 100% | 从不误拦正常用户 |
| 中风险召回率 | 100% | 不遗漏可疑用户 |
| 数据量 | 10,098 行 × 100 账户 | 模拟数据 |

---

## 速度

测试环境：Windows 10, Python 3.12, pandas 2.x

| 操作 | 耗时 | 说明 |
|------|------|------|
| 全量特征提取 (100 账户) | ~730 ms | 含 17 特征计算 |
| 单账户特征提取 | ~7 ms | 增量更新场景 |
| 规则打分 | **3.7 µs** | 纯 Python 算术，几乎零延迟 |
| XGBoost 推理 | **252 µs** | 推荐生产使用 |
| Ensemble 推理 | ~6 ms | 最准但最慢 |
| 单账户端到端 (规则) | **7.3 ms** | 提取+打分 |
| 单账户端到端 (ML) | ~14 ms | 提取+ML打分 |

---

## 项目结构

```
feature_extraction.py   # 特征提取（组员 import 入口）
scoring_model.py         # 风险打分（组员 import 入口）
train_ml_model.py        # ML 模型训练（首次运行）
evaluate.py              # 评估 CLI（python evaluate.py full）
shap_analysis.py         # 特征重要性分析
tests/                   # pytest (43 cases)
data/splits/             # 数据划分（70/15/15）
data/model/              # 训练好的模型文件
```

---

## 已知局限

| 局限 | 原因 | 缓解措施 |
|------|------|---------|
| 训练样本 69 账户 → ML 过拟合 | 模拟数据共 100 账户 | Ensemble 正则化 + 规则兜底 |
| 4 个特征恒为 0（设备复用/登录失败等） | 数据生成的角色故事特性 | 保留特征，数据变化后自动激活 |
| 无实时打分能力 | 当前为批处理模式 | 单次 <15ms，API 封装即可 |

---

## 依赖

`pyproject.toml` 中已声明，`uv sync` 自动安装：

```
numpy, pandas, scikit-learn, joblib, shap, xgboost
```
```
