# CLAUDE.md — 智能风控引擎 · 特征提取与风险打分

**Version:** 1.1.0 | **Last updated:** 2026-06-23
**项目：** 智能金融平台-模拟风控引擎 | **GitHub：** https://github.com/xiangu152/Risk-Emgine
**北理工智能风控系统 — 结课作业**

> **变更契约：** API 契约（特征键名、值域、函数签名）变更需同步更新版本号与日期。破坏性变更需通知所有组员。

---

## 项目背景

本项目从多维行为日志中提取欺诈特征并生成风险评分。整体 pipeline：

```
数据生成(@廖文远，DDL: 2026-06-24) → 特征提取(我) → 风险打分(我) → 等级划分 → 可视化
```

**我的职责范围：**
- 特征提取（`feature_extraction.py`）：从 CSV 行为日志计算欺诈特征
- 风险打分模型（`scoring_model.py`）：综合特征输出 0~100 风险分

**不负责：** 数据模拟生成（@廖文远）、可视化展示、前后端开发（其他组员负责）。

**数据生成约定：** 数据模块输入参数 `start_date, end_date, output_dir, mode, num_accounts`；输出 `${start_date}_${end_date}_risk.csv`。`mode=train` 含 `label` 列（0/1/2），`mode=test` 无标签。数据基于角色故事生成，保证同账户行为逻辑一致。
**`@data:` 锚点：** 文档中用 `@data: <相对路径>` 标记输入数据源位置（如 `@data: output/20260601_20260630_risk.csv`），供人类快速定位，不依赖自动解析。

### 全局偏好

全局偏好继承自 `~/.claude/CLAUDE.md`，关键约定推广至本项目：
- **用户指令：** 成熟的追求前沿技术的 AI Agent/全栈开发工程师，优先中文，uv 管理 Python 依赖，TDD+SDD 开发。

---

## API 契约 — extract_features()

组员主要集成入口。输出 dict 可直接传入 `score_risk()`。

```python
def extract_features(csv_path: str) -> dict[str, float]:
    """从行为日志 CSV 提取欺诈特征向量。

    Raises:
        ValueError: CSV 无法读取、为空、或缺少必填字段时抛出。
    """
```

**返回 dict 结构（共 7 个特征键）：**

| 键名 | 类型 | 值域 | 含义 |
|------|------|------|------|
| `device_reuse_ratio` | float | 0.0~1.0 | 设备复用率（基于 `machine` 字段） |
| `ip_change_freq` | float | 0.0~1.0 | IP 变更频率（归一化） |
| `tx_freq` | float | >=0.0 | 交易频率（原始计数） |
| `login_fail_ratio` | float | 0.0~1.0 | 登录失败率 |
| `amount_anomaly_score` | float | 0.0~1.0 | 金额异常分数（基于 `money_size`） |
| `behavior_time_anomaly` | float | 0.0~1.0 | 行为耗时异常（基于 `behavior_period_time`） |
| `multi_region_risk` | float | 0.0/1.0 | 多地区风险（基于 `region`） |

**JSON 输出示例：**

```json
{
  "device_reuse_ratio": 0.82,
  "ip_change_freq": 0.45,
  "tx_freq": 12.0,
  "login_fail_ratio": 0.30,
  "amount_anomaly_score": 0.67,
  "behavior_time_anomaly": 0.15,
  "multi_region_risk": 0.0
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

新增 per-user 模式，为每个用户独立计算特征向量，避免欺诈用户被正常用户稀释。

```python
def extract_features_per_user(csv_path: str) -> dict[str, dict[str, float]]:
    """返回 {user_id: {feature_name: value}}，每个用户独立评分。

    Raises:
        ValueError: CSV 无法读取、为空、或缺少必填字段时抛出。
    """
```

**与 `extract_features()` 的关系：**
- 两者共享 `_load_and_validate()` 完成 CSV 读取、校验和时间戳解析
- `extract_features()` 对所有用户取平均（聚合模式），返回单个 `dict[str, float]`
- `extract_features_per_user()` 为每个用户独立计算（per-user 模式），返回 `dict[str, dict[str, float]]`
- 各特征的**计算口径**相同（device_reuse_ratio、ip_change_freq 等），仅聚合维度不同

**返回结构示例：**

```json
{
  "u_1001": {
    "device_reuse_ratio": 0.5,
    "ip_change_freq": 0.333,
    "tx_freq": 2.0,
    "login_fail_ratio": 0.333,
    "amount_anomaly_score": 0.15
  },
  "u_1002": {
    "device_reuse_ratio": 0.5,
    "ip_change_freq": 0.333,
    "tx_freq": 1.0,
    "login_fail_ratio": 0.5,
    "amount_anomaly_score": 0.10
  }
}
```

**per-user 模式：** 每个用户独立计算 5 个特征（amount_anomaly_score 使用全局 MAD 稳健 Z-score，各用户取其交易异常分均值）。无对应事件或无交易用户该特征为 0.0。

---

## CSV 数据格式

> ⚠️ **约定草案** — 以下字段需与 @廖文远 的数据生成模块对齐。`label` 字段仅训练模式存在。

输入文件：`{start_date}_{end_date}_risk.csv`（由数据生成模块产出）。

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | `account_id` | str | 账户唯一标识 |
| 2 | `account_name` | str | 账户名称 |
| 3 | `region` | str | 地区（数据保证同一账户行为日志 region 一致） |
| 4 | `pub_time` | datetime | 行为发生时间 |
| 5 | `ip_address` | str | IP 地址 |
| 6 | `type` | str | 行为类型：`login` / `register` / `transaction` |
| 7 | `machine` | str | 设备标识（设备指纹） — **设备复用特征的核心字段** |
| 8 | `behavior_type` | str | 行为细分类型（如 `login_fail`、`tx_success` 等） |
| 9 | `behavior_period_time` | float | 行为持续时间（秒） |
| 10 | `behavior_log` | str | 行为日志描述 |
| 11 | `money_size` | float | 交易金额（非交易行为为 0） |
| 12 | `sign_up_time` | datetime | 账户注册时间 |
| 13 | `label` | int | 风险标签（仅训练模式）：0=低风险, 1=中风险, 2=高风险 |

**数据特性：** 基于角色故事生成，同一账户的 region/machine/行为模式具有逻辑一致性。训练模式含 label 用于验证打分模型准确性。

---

## 特征定义（键名与 API 契约一致）

> 以下 7 个特征基于上述 CSV 13 个字段计算。`label` 列仅用于训练阶段验证。

### 1. `device_reuse_ratio` — 设备复用率

- **业务含义：** 同一设备关联的账户数占总账户数的比例。高值表示设备被多账户共享，可能是设备农场。
- **核心字段：** `machine`（设备指纹）
- **计算逻辑：** 对每个用户，取其使用过的设备中被最多用户共享的设备的复用率（该 `machine` 关联的不同 `account_id` 数 / 总 `account_id` 数），然后对所有用户取平均值。
- **值域：** 0.0~1.0

### 2. `ip_change_freq` — IP 变更频率

- **业务含义：** 24h 窗口内 IP 切换次数归一化值。高频率 IP 变更可能意味着代理/VPN 隐藏真实位置。
- **核心字段：** `ip_address`, `pub_time`
- **计算逻辑：** 统计每个 `account_id` 在 24h 滑动窗口内使用的不同 `ip_address` 数，除以最大可能 IP 数归一化到 0.0~1.0。
- **值域：** 0.0~1.0

### 3. `tx_freq` — 交易频率

- **业务含义：** 24h 窗口内交易总次数。异常高频交易是盗刷/洗钱的典型信号。
- **核心字段：** `type`, `pub_time`
- **计算逻辑：** 统计每个 `account_id` 在 24h 内 `type == "transaction"` 的事件数。使用原始计数，不做归一化（后续由 `score_risk` 加权处理）。
- **值域：** >=0.0（float，原始计数）

### 4. `login_fail_ratio` — 登录失败率

- **业务含义：** 登录失败次数占总登录尝试次数的比例。高失败率意味着暴力破解或账户接管尝试。
- **核心字段：** `type`, `behavior_type`
- **计算逻辑：** `behavior_type` 包含 "fail" 字样的 login 事件数 / login 总事件数。
- **值域：** 0.0~1.0

### 5. `amount_anomaly_score` — 金额异常分数

- **业务含义：** 交易金额偏离整体交易均值的程度。大额偏离可能是盗刷后快速变现。
- **核心字段：** `money_size`, `type`
- **计算逻辑：** 基于 `money_size > 0` 的交易记录的 MAD 稳健 Z-score（中位数 + 中位数绝对偏差），抵抗极端值遮蔽。|robust_z| >= 3 时得分趋于 1.0。
- **值域：** 0.0~1.0

### 6. `behavior_time_anomaly` — 行为耗时异常（v1.1.0 新增）

- **业务含义：** 自动化脚本操作极快（<1s），与正常用户操作节奏明显不同。
- **核心字段：** `behavior_period_time`
- **计算逻辑：** `behavior_period_time < 1.0` 秒的行为占比。
- **值域：** 0.0~1.0

### 7. `multi_region_risk` — 多地区风险（v1.1.0 新增）

- **业务含义：** 同一账户短时间在不同地区活动物理上不可能，是账户被盗/共用的强信号。
- **核心字段：** `region`, `account_id`
- **计算逻辑：** 按 `account_id` 分组统计 `region` 的唯一值数量。存在多地区的账户时标记 1.0，否则 0.0。
- **值域：** 0.0 或 1.0（布尔型）

---

## API 契约 — score_risk()
风险打分函数，接收特征向量，输出 0~100 风险评分。

```python
def score_risk(features: dict[str, float]) -> dict[str, float | str]:
    """加权求和 + 规则增强，计算综合风险评分"""
```

- **评分方法：** 加权求和（各特征 × 权重求和，再缩放到 0~100）+ 规则增强（加分项，可叠加）：
  1. `device_reuse_ratio > 0.9 且 tx_freq > 50` — 设备农场+高频交易 → +10
  2. `ip_change_freq > 0.8 且 login_fail_ratio > 0.5` — IP频繁变更+撞库 → +10
  3. `amount_anomaly_score > 0.7` — 单维度金额极端异常 → +15
  4. `login_fail_ratio > 0.7` — 单维度暴力破解 → +20
  5. `device_reuse_ratio > 0.2` — 设备共享（多账户共用设备）→ +19
  6. `ip_change_freq > 0.1 且 amount_anomaly_score > 0.3` — 账户盗用（IP变更+大额交易）→ +15
  7. `device_reuse_ratio > 0.15 且 login_fail_ratio > 0.3` — 设备农场撞库（共享设备+试密码）→ +15
  8. `tx_freq > 10 且 amount_anomaly_score > 0.3` — 洗钱模式（高频+高额交易）→ +15
  9. `behavior_time_anomaly > 0.5 且 tx_freq > 20` — 自动化脚本跑量（⚡快+量大）→ +15（v1.1.0）
  10. `multi_region_risk > 0` — 多地区异常（物理不可能）→ +12（v1.1.0）
- **默认权重（可调）：**

| 特征键名 | 权重 |
|----------|------|
| `device_reuse_ratio` | 0.20 |
| `ip_change_freq` | 0.15 |
| `tx_freq` | 0.15（先归一化 `min(1.0, tx_freq/100)`） |
| `login_fail_ratio` | 0.15 |
| `amount_anomaly_score` | 0.15 |
| `behavior_time_anomaly` | 0.10（v1.1.0） |
| `multi_region_risk` | 0.10（v1.1.0） |

- **输入来源：** 直接接收 `extract_features()` 的返回值。

**JSON 输入示例（来自 extract_features 输出，7 个特征）：**

```json
{
  "device_reuse_ratio": 0.82,
  "ip_change_freq": 0.45,
  "tx_freq": 12.0,
  "login_fail_ratio": 0.30,
  "amount_anomaly_score": 0.67,
  "behavior_time_anomaly": 0.15,
  "multi_region_risk": 0.0
}
```

**JSON 输出示例：**

```json
{
  "score": 64.8,
  "level": "MEDIUM",
  "level_range": "31~70"
}
```

---

## 风险等级
| 等级 | 分值范围 | 等级标识（level 字段） | 说明 |
|------|----------|----------------------|------|
| 低风险 | 0~30 | `"LOW"` | 行为正常，无需关注 |
| 中风险 | 31~70 | `"MEDIUM"` | 存在可疑模式，建议人工复核 |
| 高风险 | 71~100 | `"HIGH"` | 极可能欺诈，触发警报/拦截 |

`score_risk()` 输出 dict 中 `level` 字段为大写英文字符串，`level_range` 为字符串 `"0~30"` / `"31~70"` / `"71~100"`。

---

## 版本与开发规范
### 版本管理

- **当前版本：** 1.1.0
- **变更契约：** API 契约（特征键名、值域、函数签名、返回结构）变更时，必须同步更新顶部版本号和日期。破坏性变更需在团队内部通知所有组员。
- **语义化版本：** MAJOR.MINOR.PATCH — MAJOR 表示破坏性 API 变更，MINOR 表示新增向后兼容特性，PATCH 表示修复/文档更新。
- **1.1.0 (2026-06-23):** CSV 字段对齐真实数据规范（13 字段，详见文档）；字段名映射 `user_id→account_id`、`device_id→machine`、`event_type→type`、`timestamp→pub_time`、`amount→money_size`；新增 2 个特征 `behavior_time_anomaly`、`multi_region_risk`（向后兼容，旧 5 特征键名不变但基于新字段名计算）；打分权重重新分配至 7 特征；新增 2 条规则增强（#9 自动化脚本跑量、#10 多地区异常）。
- **1.0.0 -> 1.0.1:** extract_features() 不再静默返回全零特征向量，改为抛出 ValueError。调用方需捕获异常。
### 开发偏好
- **语言 & 工具链：** Python 3.10+，Pandas 数据处理
- **依赖管理：** `uv`（`uv add pandas`、`uv add pytest --dev`）
- **开发方式：** TDD（先写测试，再写实现）+ SDD（规范驱动，API 契约先行）
- **项目结构：** `feature_extraction.py` + `scoring_model.py` + `tests/`
- **类型注解：** 所有公共函数必须使用完整的 Python type hints。
- **代码风格：** surgical changes（只改任务要求的部分），simplicity first（最小编写），无临时调试代码残留。

### 集成示例

```python
from feature_extraction import extract_features
from scoring_model import score_risk

features = extract_features("data/behavior_logs.csv")
result = score_risk(features)
print(result)  # {"score": 64.8, "level": "MEDIUM", "level_range": "31~70"}
```
