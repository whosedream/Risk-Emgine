# Plan: 反欺诈特征提取与打分模型 CLAUDE.md

**Status:** completed
**Based on:** `.omc/specs/deep-interview-antifraud-features.md`
**Created:** 2026-06-23
**Updated:** 2026-06-23 (architecture review APPLIED_WITH_IMPROVEMENTS)

---

## RALPLAN-DR Summary

### Principles
1. **Minimal sufficient specification** — CLAUDE.md 只定义三要素（CSV字段名 + API返回结构 + 特征业务含义），避免过度约束
2. **Dual-purpose document** — 既让 AI 可自主生成代码，也让组员可直接集成 API
3. **Interpretability over complexity** — 风险打分模型优先可解释性（加权求和），不引入 ML 框架
4. **API-first thinking** — 每个模块先定义清晰的输入/输出接口，再考虑实现细节
5. **Convention over configuration** — 继承用户全局偏好（TDD、uv、中文优先），不重复声明

### Decision Drivers
1. **团队协作边界** — 必须定义清晰 API 让前后端组员无需询问即可集成（最高优先级）
2. **AI 可用性** — CLAUDE.md 需包含足够上下文让 AI 生成可运行代码
3. **文档简洁性** — 不超过 200 行，避免信息过载

### Viable Options
| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: 单文件 CLAUDE.md | 一个文件覆盖所有内容：项目背景 → 特征定义 → API → 偏好 | 简单、传统、AI 一次读取 | 特征和打分逻辑混在一起，API 部分不够突出 |
| B: CLAUDE.md + docs/api.md | CLAUDE.md 写项目背景和偏好，API 细节放 docs/ | API 文档独立可维护 | 多文件增加认知负担，AI 可能忽略 docs/ |
| C: 结构化的 CLAUDE.md 单文件 | 单文件用清晰 Markdown 分区（## 项目背景 → ## API 契约 → ## 数据格式 → ## 特征定义 → ## 偏好），每节简短 | 一次读取 + 模块清晰 | 需要精心组织，控制篇幅 |

**推荐: Option C** — 单文件结构化分区，API 契约紧接项目背景之后，优先人类可发现性。

### ADR (Architecture Decision Record)
- **Decision:** 采用 Option C — 结构化单文件 CLAUDE.md，章节顺序为：项目背景 → API 契约（最前）→ 数据格式 → 特征定义 → 偏好/规范
- **Drivers:** 组员集成 API 是最频繁的操作场景，API 契约前移最小化查找成本；单文件保持 AI 一次读取的便利性
- **Alternatives considered:** Option A（API 不够突出）、Option B（多文件认知负担）
- **Why chosen:** Option C 兼顾简洁性和可发现性，章节重排序后 API 契约成为第二章节，组员打开文件即可看到集成接口
- **Consequences:** 需要精心控制篇幅（≤200 行），特征定义章节需引用前方的 API 契约作为上下文
- **Follow-ups:** 实际使用后根据组员反馈调整章节粒度

---

## Requirements Summary
编写一份个人开发用 CLAUDE.md，覆盖反欺诈规则挖掘项目中的特征提取和风险打分模型模块。文件为双用途：AI 助手读取后能生成可运行代码，组员读取后能直接集成 API。

## Acceptance Criteria (from Deep Interview Spec)
- [ ] CLAUDE.md 包含项目背景（反欺诈规则挖掘）和用户的职责范围说明
- [ ] CLAUDE.md 定义了 CSV 输入数据的字段结构（登录、注册、交易等行为日志字段），含 `timestamp` 格式约定
- [ ] CLAUDE.md 明确列出所有需提取的特征及其业务含义和计算逻辑（设备复用率、IP频繁变更、交易频率等）
- [ ] CLAUDE.md 定义了 `extract_features()` 的返回 dict 结构（键名、值域、数据类型）—— 这是组员的主要集成点
- [ ] CLAUDE.md 定义了风险打分模型 `score_risk()` 的 API 接口（输入：特征dict → 输出：0~100分），含 JSON 示例
- [ ] CLAUDE.md 包含版本号/更新日期和变更契约约定
- [ ] CLAUDE.md 包含了用户的个人开发偏好（TDD、uv、Pandas）
- [ ] 组员仅凭 CLAUDE.md 就能写出调用 `extract_features()` + `score_risk()` 的代码
- [ ] AI 助手能根据 CLAUDE.md 自主生成可运行的特征提取和打分模型代码

## Implementation Steps

### Step 1: 定义 CSV 输入数据格式（数据契约）
**文件：** `CLAUDE.md`
**内容：** 定义行为日志 CSV 的字段结构
```
- 字段名、类型、含义、示例值
- user_id (str), event_type (login|register|transaction), device_id (str), ip_address (str), timestamp (str, ISO 8601), amount (float)
- timestamp 格式：ISO 8601，示例 `2024-01-15T14:30:00Z`
- 明确标注字段为"约定草案，需与数据模拟组对齐"
```
**Acceptance criteria:**
- 所有 6 个字段均定义了名称、类型、含义
- `timestamp` 字段明确标注 ISO 8601 格式及示例值

### Step 2: 定义特征列表与计算逻辑
**文件：** `CLAUDE.md`
**内容：** 每个特征包含——
- 名称（中英文）
- 业务含义（一句话解释为什么它是欺诈指标）
- 计算逻辑（伪代码或公式）
- 输出值域（如 0.0~1.0）
- 特征列表：
  1. device_reuse_ratio — 设备复用率 = 同设备关联账户数 / 总账户数，值域 0.0~1.0
  2. ip_change_freq — IP变更频率 = 单位时间（24h）内不同IP数，值域 0.0~1.0（归一化后）
  3. tx_freq — 交易频率 = 单位时间（24h）内交易次数，值域 float（原始计数或归一化）
  4. 其他辅助特征（如 login_fail_ratio、amount_anomaly_score 等）
**注意：** 本章节顺序排在"API 契约"之后（见 Step 3），形成"先看接口、再看实现细节"的阅读流。
**Acceptance criteria:**
- 至少列出 3 个核心特征的完整定义（名称、含义、公式、值域）
- 特征键名与 Step 3 的 `extract_features()` 返回 dict 键名一致

### Step 3: 定义 extract_features() API 契约（主要集成点）
**文件：** `CLAUDE.md`
**插入位置：** "## 项目背景"章节之后的最前面（第二章节），优先人类可发现性
**内容：**
```
函数签名：extract_features(csv_path: str) -> dict[str, float]

返回 dict 结构：
{
    "device_reuse_ratio": float,      # 0.0~1.0，设备复用率
    "ip_change_freq": float,          # 0.0~1.0，IP变更频率（归一化）
    "tx_freq": float,                 # ≥0.0，交易频率（原始计数）
    "login_fail_ratio": float,        # 0.0~1.0，登录失败率
    "amount_anomaly_score": float     # 0.0~1.0，金额异常分数
}

JSON 输出示例：
{
  "device_reuse_ratio": 0.82,
  "ip_change_freq": 0.45,
  "tx_freq": 12.0,
  "login_fail_ratio": 0.30,
  "amount_anomaly_score": 0.67
}
```
- 明确标注每个键的数据类型和值域约束
- 注明：这是组员集成的主要入口，输出 dict 可直接传入 `score_risk()`
**Acceptance criteria:**
- 返回 dict 的每个键名、类型、值域均已定义
- 包含至少一个完整的 JSON 输出示例
- 组员无需查看实现代码即可据此调用

### Step 4: 定义 score_risk() API（打分模型）
**文件：** `CLAUDE.md`
**内容：**
- 输入接口：`score_risk(features: dict[str, float]) -> dict[str, float | str]`
- 评分方法：加权求和 + 规则增强（如特定模式下加分）
- 权重由 AI 根据反欺诈常识设定（透明可调）
- 风险等级映射：0~30 低风险 / 31~70 中风险 / 71~100 高风险
- JSON 输入/输出示例：

```
输入示例（来自 extract_features 的输出）：
{
  "device_reuse_ratio": 0.82,
  "ip_change_freq": 0.45,
  "tx_freq": 12.0,
  "login_fail_ratio": 0.30,
  "amount_anomaly_score": 0.67
}

输出示例：
{
  "score": 68.5,
  "level": "MEDIUM",
  "level_range": "31~70"
}
```
**Acceptance criteria:**
- 函数签名明确定义输入 dict 和输出 dict 的结构
- 包含至少一对输入/输出 JSON 示例
- 输出 dict 包含 `score`（float）和 `level`（str）两个字段

### Step 5: 定义风险等级输出结构
**文件：** `CLAUDE.md`
**内容：**
- 等级枚举：LOW / MEDIUM / HIGH
- 分值映射关系（0~30 / 31~70 / 71~100）
- 输出 `level_range` 字段说明
- 此步骤内容与 Step 4 的输出示例保持一致
**Acceptance criteria:**
- 三个等级的名称和分值区间明确定义
- 与 Step 4 的 `score_risk()` 输出结构无矛盾

### Step 6: 写入版本管理与开发规范
**文件：** `CLAUDE.md`
**内容：**
- **版本号与更新日期** — 在 CLAUDE.md 顶部标注 `Version: 1.0.0` 和 `Last updated: YYYY-MM-DD`
- **变更契约约定** — 声明：API 契约变更需同步更新版本号和日期；破坏性变更需通知所有组员
- TDD + SDD 开发方式
- uv 管理 Python 依赖（`uv add pandas`）
- 优先说中文
- Python 类型注解要求
- 代码风格：surgical changes, simplicity first
**Acceptance criteria:**
- CLAUDE.md 顶部包含版本号和更新日期
- 包含变更契约约定（如何通知 API 变更）

### Step 7: 编写项目背景和职责说明
**文件：** `CLAUDE.md`
**章节顺序：** 此为 CLAUDE.md 的第一章节
**内容：**
- 项目名称和一句话目标
- 用户职责范围（特征提取 + 打分模型）
- 团队分工说明（数据模拟、可视化由其他组员负责）
- 引用全局 CLAUDE.md 中的通用指令
- `@data:` 锚点机制：明确定义为"数据源路径引用标记"，格式 `@data: <相对路径或描述>`，用于在文档中快速定位输入数据来源，不依赖任何自动化解析
**Acceptance criteria:**
- 项目背景不超过 10 行
- `@data:` 锚点有明确定义和用法说明

### Step 8: 验证
**文件：** `CLAUDE.md`
**验证项：**
1. 检查 CLAUDE.md 行数 ≤ 200
2. 检查 9 项验收标准全绿
3. 模拟 AI 视角：能否据此生成 `feature_extraction.py` 和 `scoring_model.py`
4. 模拟组员视角：能否据此写出调用 `extract_features()` + `score_risk()` 的集成代码
5. CSV 字段定义：Grep 检查是否包含 `user_id`, `device_id`, `ip_address` 等关键字段及 `timestamp` 格式
6. 特征完整性：Grep 检查是否包含设备复用率、IP变更、交易频率的计算描述
7. API 清晰度：检查 `extract_features()` 返回 dict 结构和 `score_risk()` 输入/输出是否明确定义
8. 行数约束：`(Get-Content CLAUDE.md | Measure-Object -Line).Lines` ≤ 200

**Acceptance criteria:**
- 所有 8 项验证通过
- 特别检查项：仅凭 CLAUDE.md，能否写出 `from feature_extraction import extract_features; from scoring_model import score_risk; features = extract_features("data.csv"); result = score_risk(features); print(result)` 这样的调用代码（答案应为"是"）

## Files to Create/Modify
| File | Action | Description |
|------|--------|-------------|
| `D:\CodeField\ruleSys\CLAUDE.md` | CREATE | 项目级个人开发指令文件 |

## Risks and Mitigations
| Risk | Severity | Mitigation |
|------|----------|------------|
| CLAUDE.md 过于冗长导致 AI 忽略关键信息 | Medium | 控制在 200 行内，API 契约前置保障可发现性 |
| CSV 字段设计与组员实际数据不一致 | Medium | 在 CLAUDE.md 中明确标注字段为"约定草案，需对齐"；timestamp 格式已锁定为 ISO 8601 |
| 打分模型权重定义过于随意 | Low | 注明权重可根据实际数据调优，提供默认值即可 |
| extract_features 键名与 score_risk 输入不匹配 | Low | 在 CLAUDE.md 中明确声明 score_risk 的输入 dict 直接来自 extract_features 的输出，保持键名一致 |

## Verification Steps
1. 文件存在性：`Test-Path CLAUDE.md`
2. CSV 字段定义：Grep 检查是否包含 `user_id`, `device_id`, `ip_address`, `timestamp` 等关键字段，且 `timestamp` 含 ISO 8601 格式说明
3. 特征完整性：Grep 检查是否包含 device_reuse_ratio、ip_change_freq、tx_freq 等特征键名及计算描述
4. extract_features API：Grep 检查 `extract_features` 函数签名和返回 dict 结构定义
5. score_risk API：Grep 检查 `score_risk` 函数签名、输入/输出 JSON 示例
6. 独立集成能力：仅凭 CLAUDE.md 内容，人工判断能否写出调用 extract_features() + score_risk() 的完整代码
7. 版本信息：Grep 检查是否包含版本号和更新日期
8. 行数约束：`(Get-Content CLAUDE.md | Measure-Object -Line).Lines` ≤ 200
9. 验收标准：逐项对照 9 条 AC 检查覆盖

---

## Changelog
- 2026-06-23 (round 1): 架构审查 APPROVED_WITH_IMPROVEMENTS — 关键修改：插入 Step 3 `extract_features()` API 契约（组员主要集成点），Step 1 timestamp 格式锁定为 ISO 8601；重要修改：API 契约章节前移至项目背景之后，API 契约包含 JSON 输入/输出示例，Step 6 新增版本号与变更契约约定；建议修改：`@data:` 锚点明确定义为路径引用标记，验证新增"仅凭 CLAUDE.md 能否写出调用代码"检查项。步骤从 7 步扩展为 8 步，验收标准从 7 条扩展为 9 条。
- 2026-06-23 (round 0): Initial plan created by Planner (consensus round 0)
- 2026-06-23 (round 2): 执行完成 — CLAUDE.md 创建 (131行)，feature_extraction.py + scoring_model.py 实现，33 测试全绿，spec-impl 三项一致性修复（JSON 示例数值、默认权重表、numpy 依赖）。
