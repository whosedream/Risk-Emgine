"""
行为数据生成提示词
"""

import json

BEHAVIOR_SYSTEM_PROMPT = """你是一个数据生成专家，负责为反欺诈系统生成逼真的用户行为日志数据。
你需要根据用户的角色故事，生成符合其行为模式的时间序列行为数据。"""

BEHAVIOR_PROMPT = """根据以下角色故事和时间范围，生成该用户的行为日志数据。

角色故事：
{role_story}

时间范围：{start_date} 到 {end_date}
模式：{mode}（train 模式包含 label，test 模式不包含）

请生成该用户在时间范围内的所有行为记录，每条记录包含：
1. pub_time: 行为发生时间（ISO 8601 格式）
2. ip_address: IP 地址（根据地区生成合理的 IP）
3. type: 行为类型（login/register/transaction/browse/search/comment）
4. behavior_type: 行为细分类型
5. behavior_period_time: 行为持续时间（秒，1-3600之间）
6. behavior_log: 行为日志描述（简短描述该行为）
7. money_size: 交易金额（非交易行为为 0）

行为生成规则：
- 低风险用户：行为规律，交易金额正常，设备和IP稳定
- 中风险用户：有一定异常行为，但整体可控
- 高风险用户：频繁更换设备/IP，异常时间段活跃，交易金额异常

{mode_instruction}

请以 JSON 数组格式返回，示例：
```json
[
  {{
    "pub_time": "2026-06-01T09:30:00",
    "ip_address": "192.168.1.100",
    "type": "login",
    "behavior_type": "normal_login",
    "behavior_period_time": 15,
    "behavior_log": "用户正常登录",
    "money_size": 0
  }}
]
```"""


def get_behavior_prompt(role_story: dict, start_date: str, end_date: str, mode: str) -> str:
    """获取行为数据生成提示词"""
    if mode == "train":
        mode_instruction = "训练模式：请在每条记录中添加 label 字段，值为用户的风险等级（0/1/2）。"
    else:
        mode_instruction = "测试模式：不要添加 label 字段。"

    return BEHAVIOR_PROMPT.format(
        role_story=json.dumps(role_story, ensure_ascii=False, indent=2),
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        mode_instruction=mode_instruction
    )
