"""
提示词模块

导出：
- role_templates: 角色模板定义（创建）
- role_loader: 角色加载器（加载）
- behavior: 行为数据生成提示词
"""

from .role_templates import ALL_TEMPLATES, RISK_DISTRIBUTION
from .role_loader import (
    load_role_templates,
    get_random_template,
    generate_account_with_template,
    select_risk_level,
    generate_accounts
)
from .behavior import get_behavior_prompt

__all__ = [
    "ALL_TEMPLATES",
    "RISK_DISTRIBUTION",
    "load_role_templates",
    "get_random_template",
    "generate_account_with_template",
    "select_risk_level",
    "generate_accounts",
    "get_behavior_prompt"
]
