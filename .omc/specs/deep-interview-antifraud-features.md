# Deep Interview Spec: 反欺诈特征提取与打分模型 CLAUDE.md

## Metadata
- Interview ID: di-20260623-antifraud-features
- Rounds: 6
- Final Ambiguity Score: 19.5%
- Type: greenfield
- Generated: 2026-06-23T13:30:00+08:00
- Threshold: 0.2 (20%)
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.85 | 0.40 | 0.34 |
| Constraint Clarity | 0.80 | 0.30 | 0.24 |
| Success Criteria | 0.75 | 0.30 | 0.225 |
| **Total Clarity** | | | **0.805** |
| **Ambiguity** | | | **19.5%** |

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| feature-extraction | active | 从CSV行为日志中计算欺诈指标：设备复用率、账户IP频繁变更、交易频率等 | API 返回结构 + 特征业务含义 + CSV 输入字段名 |
| risk-scoring-model | active | 设计0~100分的复合评分函数，综合各特征输出风险分值 | 评分函数 API（输入特征向量 → 输出0~100分），AI 自选简单可解释方法 |
| data-viz | deferred | 生成100+条模拟数据、Pandas读写处理、风险等级划分、可视化图表 | 用户确认非直接负责部分，CLAUDE.md 简要提及但不作为深度访谈重点 |

## Goal
编写一份个人开发用 CLAUDE.md 文件，放置在用户工作区目录下，作为 AI 助手的全面开发指令。该文件需覆盖：
1. **特征提取模块**和**风险打分模型模块**的完整业务逻辑和技术约束
2. 清晰定义模块间 API（CSV 输入字段名、特征输出结构、打分函数签名），确保其他组员的前后端可直接集成
3. 包含用户的个人开发偏好（TDD、uv 管理依赖、Pandas），同时让 AI 可以根据 CLAUDE.md 自主生成可运行代码

## Constraints
- 最小必要约束三要素：CSV 输入字段名 + API 返回数据结构 + 每个特征的业务含义和计算逻辑
- 技术栈方向：Python + Pandas，但不锁定具体实现细节（函数签名、文件结构由 AI 自主决策）
- 模型复杂度：AI 自选简单可解释的方法（加权求和、规则引擎等），不需要引入机器学习框架
- 个人偏好集成：TDD 开发方式、uv 管理 Python 依赖
- API 设计需包含明确的输入/输出格式，使组员无需再次询问即可集成

## Non-Goals
- 不定义完整的前后端架构
- 不编写实际的特征提取和打分模型代码（CLAUDE.md 是规范文档，代码在后续开发）
- 不负责数据模拟生成、可视化展示（由其他组员负责）
- 不引入复杂的机器学习模型

## Acceptance Criteria
- [ ] CLAUDE.md 包含项目背景（反欺诈规则挖掘）和用户的职责范围说明
- [ ] CLAUDE.md 定义了 CSV 输入数据的字段结构（登录、注册、交易等行为日志字段）
- [ ] CLAUDE.md 明确列出所有需提取的特征及其业务含义和计算逻辑（设备复用率、IP频繁变更、交易频率等）
- [ ] CLAUDE.md 定义了风险打分模型的 API 接口（输入：特征向量 → 输出：0~100分）
- [ ] CLAUDE.md 包含了用户的个人开发偏好（TDD、uv、Pandas）
- [ ] 组员能根据 CLAUDE.md 中的 API 定义直接集成，无需额外询问
- [ ] AI 助手能根据 CLAUDE.md 自主生成可运行的特征提取和打分模型代码

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| CLAUDE.md 只需描述业务逻辑 | Round 4 Contrarian: 如果不写技术约束会怎样？ | 必须有 API 级技术约束，因为后续组员需要据此开发前后端 |
| 需要完整的技术规范（错误处理、性能等） | Round 6 Simplifier: 最少需要什么约束？ | 只需要三要素：CSV字段名 + API返回结构 + 特征业务含义 |
| 模型需要机器学习方法 | Round 3 提问 | AI 自选简单可解释方法，不需要引入 ML 框架 |
| CLAUDE.md 只给 AI 看 | Round 1 提问 | 双用途：既给 AI 助手生成代码，也给组员作为 API 文档 |

## Technical Context
- **项目类型**: Greenfield（空目录），从零开始
- **语言**: Python
- **核心依赖**: Pandas（数据处理）
- **依赖管理**: uv
- **开发方式**: TDD（测试驱动开发）+ SDD（规范驱动开发）
- **开发环境**: Windows 10, PowerShell
- **全局用户指令**: 用户全局 CLAUDE.md 已配置 oh-my-claudecode 多智能体编排、优先中文、uv 管理、TDD+SDD 模式

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| CLAUDE.md | core domain | 内容, 受众:个人+AI, 位置:项目工作区 | CLAUDE.md 指导 AI 开发 特征提取 和 风险打分模型 |
| 行为日志 (Behavioral Log) | core domain | 格式:CSV, 事件类型:登录/注册/交易, 字段:用户ID/设备ID/IP/时间戳/交易金额 | 行为日志 输入到 特征提取 |
| 特征 (Feature) | core domain | 名称, 计算逻辑, 业务含义 | 特征 由 特征提取 计算, 特征 输入到 风险打分模型 |
| 风险评分 (Risk Score) | core domain | 范围:0-100 | 风险评分 由 风险打分模型 计算, 风险评分 划归 账户 |
| 账户 (Account) | core domain | 用户ID, 风险等级 | 账户 拥有 风险评分 |
| 个人偏好 (Personal Preference) | supporting | TDD, uv管理依赖, 优先中文 | 个人偏好 嵌入 CLAUDE.md |
| API接口 (API Interface) | supporting | 输入格式, 输出格式 | API接口 连接 特征提取 到 前后端系统, API接口 连接 风险打分模型 到 前后端系统 |
| 前后端系统 (Front/Back End) | external system | — | 前后端系统 调用 API接口 |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|-----------------|
| 1 | 5 | 5 | - | - | N/A |
| 2 | 6 | 1 | 0 | 5 | 83% |
| 3 | 6 | 0 | 0 | 6 | 100% |
| 4 | 8 | 2 | 0 | 6 | 75% |
| 5 | 8 | 0 | 0 | 8 | 100% |
| 6 | 8 | 0 | 0 | 8 | 100% |

## Interview Transcript
<details>
<summary>Full Q&A (6 rounds)</summary>

### Round 0 (Topology)
**Q:** 拓扑确认 — 3个顶层组件（特征提取、风险打分模型、数据与可视化）
**A:** 延后数据/可视化（非直接负责），前两个激活

### Round 1
**Q:** CLAUDE.md 的主要受众和使用场景？
**A:** 个人开发指令 — 给 AI 助手读取，指导后续编码行为
**Ambiguity:** 82% (Goal: 0.30, Constraints: 0.10, Criteria: 0.10)

### Round 2
**Q:** CLAUDE.md 对 AI 的指令力度？
**A:** C — 全面指令，既含项目背景也含个人偏好（TDD、uv），减少手动说明
**Ambiguity:** 73% (Goal: 0.45, Constraints: 0.15, Criteria: 0.15)

### Round 3
**Q:** 风险打分模型的技术复杂度？
**A:** C — AI 自选，根据"简单、可解释"原则
**Ambiguity:** 66.5% (Goal: 0.50, Constraints: 0.25, Criteria: 0.20)

### Round 4 (Contrarian)
**Q:** 如果不写技术约束会怎样？
**A:** 必须有 API 级约束，因为后续要给其他组员写前后端
**Ambiguity:** 48.5% (Goal: 0.65, Constraints: 0.50, Criteria: 0.35)

### Round 5
**Q:** 验收标准是什么？
**A:** 两者都要 — 组员可集成 + AI 可生成代码
**Ambiguity:** 31% (Goal: 0.75, Constraints: 0.60, Criteria: 0.70)

### Round 6 (Simplifier)
**Q:** 最小必要约束是什么？
**A:** 三要素足够 — CSV字段名 + API返回结构 + 特征业务含义
**Ambiguity:** 19.5% (Goal: 0.85, Constraints: 0.80, Criteria: 0.75) ✅ 达标

</details>
