# 多维行为日志数据生成模块

## 功能描述

生成多维度的用户行为日志数据，用于反欺诈系统的特征提取与风险打分。

## 目录结构

```
data_creater/
├── __init__.py              # 公共接口：export generate_data
├── main.py                  # 入口文件（只 import + 参数解析）
├── requirements.txt         # 依赖
├── .env                     # 环境变量（不提交 git）
├── README.md                # 本文档
├── api/
│   └── llm.py              # LLM API 调用（含重试逻辑）
├── config/
│   └── settings.py          # 配置常量
├── prompts/
│   ├── __init__.py          # 导出公开接口
│   ├── role_templates.py    # 角色模板定义（创建）
│   ├── role_loader.py       # 角色加载器（加载）
│   └── behavior.py          # 行为数据生成提示词
└── script/
    └── generate.py          # 主生成脚本
```

## 架构说明

本模块采用「模板 + LLM 增强」两阶段方式生成行为日志数据。

### 第一阶段：模板生成（同步，无 LLM 调用）

- `role_templates.py` 定义了低/中/高三种风险等级的用户角色模板
- `role_loader.py` 的 `select_risk_level()` 按 6:3:1 比例随机选择风险等级
- `generate_accounts()` 批量生成账户角色故事（从模板随机选择）

### 第二阶段：LLM 增强（异步，调用 LLM）

- 对每个账户调用 LLM 增强表面细节（姓名、设备型号、行为描述）
- LLM 生成的值替换模板原值，保持结构特征不变
- 增强失败时回退到模板默认值，不中断流程

### 边界定义

| 类型 | 字段 | 说明 |
|------|------|------|
| 模板控制（不可变） | risk_level, user_profile, ip_pattern, transaction_pattern | 结构特征，由模板决定 |
| LLM 增强（替换原值） | account_name, device_info, behavior_pattern | 表面细节，由 LLM 丰富 |

## 输入参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| start_date | string | 是 | 起始日期 (YYYYMMDD) | 20260601 |
| end_date | string | 是 | 结束日期 (YYYYMMDD) | 20260630 |
| output_dir | string | 是 | 输出目录（不存在时自动创建） | ./data |
| mode | string | 是 | 模式: train / test | train |
| num_accounts | int | 否 | 生成账户数量 (默认 100) | 100 |

## 约束条件

- `start_date`、`end_date` 格式必须为 YYYYMMDD，否则报错
- `end_date >= start_date`
- `mode` 只能为 `train` 或 `test`
- `num_accounts > 0`
- `output_dir` 不存在时自动创建
- LLM 调用失败时重试 3 次，仍失败则跳过该账户

## 输出

- 在 `output_dir` 下生成 `{start_date}_{end_date}_risk.csv`
- 训练模式 (train): 包含风险标签 (label)
- 测试模式 (test): 不含风险标签

## 数据字典

| 字段 | 类型 | 说明 |
|------|------|------|
| account_id | string | 账户唯一标识（格式：ACC_XXXXX） |
| account_name | string | 账户名称（LLM 增强） |
| region | string | 地区 |
| pub_time | datetime | 行为发生时间 |
| ip_address | string | IP 地址 |
| type | string | 行为类型（login/register/transaction 等） |
| machine | string | 设备标识（来自 LLM 增强后的 device_info） |
| behavior_type | string | 行为细分类型 |
| behavior_period_time | float | 行为持续时间（秒） |
| behavior_log | string | 行为日志描述 |
| money_size | float | 交易金额（非交易行为为 0） |
| sign_up_time | datetime | 账户注册时间 |
| label | int | 风险标签（仅 train 模式）：0-低风险, 1-中风险, 2-高风险 |

## 风险等级说明

| 等级 | 标签 | 比例 | 特征 |
|------|------|------|------|
| 低风险 | 0 | 60% | 行为规律，设备/IP 稳定，交易金额正常 |
| 中风险 | 1 | 30% | 有一定异常行为，但整体可控 |
| 高风险 | 2 | 10% | 频繁换设备/IP，异常时段活跃，交易金额异常 |

## 使用方法

### 安装依赖

```bash
pip install httpx python-dotenv
```

### 配置环境变量

创建 `.env` 文件：

```
ANTHROPIC_BASE_URL=https://your-api-endpoint
ANTHROPIC_AUTH_TOKEN=your-api-key
MODEL=your-model-name
```

### 运行

```bash
# 训练模式（100 个账户）
python main.py 20260601 20260630 ./data train 100

# 测试模式（50 个账户）
python main.py 20260601 20260630 ./data test 50
```

### 作为模块导入

```python
from data_creater import generate_data

output_file = await generate_data(
    start_date="20260601",
    end_date="20260630",
    output_dir="./data",
    mode="train",
    num_accounts=100
)
```

## 数据生成逻辑

1. **模板生成**: 使用 `role_loader.generate_accounts()` 从模板随机生成账户
2. **LLM 增强**: 对每个账户调用 LLM 增强表面细节（姓名、设备、行为描述）
3. **行为生成**: 根据角色故事生成时间序列行为日志
4. **CSV 输出**: 将数据写入 CSV 文件
