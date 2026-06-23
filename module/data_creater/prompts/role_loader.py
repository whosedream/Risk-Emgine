"""
角色加载器 - 随机选择角色模板

创建和加载解耦：
- role_templates.py 定义模板（创建）
- 本文件负责加载和随机选择（加载）
"""

import json
import random
from typing import List, Dict, Any, Optional

from .role_templates import ALL_TEMPLATES, RISK_DISTRIBUTION


def load_role_templates() -> Dict[int, List[Dict]]:
    """加载所有角色模板"""
    return ALL_TEMPLATES


def get_random_template(risk_level: int) -> Dict[str, Any]:
    """根据风险等级随机选择一个模板"""
    templates = ALL_TEMPLATES.get(risk_level, ALL_TEMPLATES[0])
    return random.choice(templates)


def generate_account_with_template(account_id: str, account_name: str, region: str,
                                    sign_up_time: str, risk_level: int) -> Dict[str, Any]:
    """
    使用模板生成完整账户信息

    Args:
        account_id: 账户ID
        account_name: 账户名称
        region: 地区
        sign_up_time: 注册时间
        risk_level: 风险等级 (0/1/2)

    Returns:
        完整的账户角色故事
    """
    template = get_random_template(risk_level)

    return {
        "account_id": account_id,
        "account_name": account_name,
        "region": region,
        "sign_up_time": sign_up_time,
        "risk_level": risk_level,
        **template
    }


def select_risk_level() -> int:
    """
    根据 6:3:1 比例随机选择风险等级

    Returns:
        0 (低风险), 1 (中风险), 或 2 (高风险)
    """
    rand = random.random()
    if rand < 0.6:
        return 0
    elif rand < 0.9:
        return 1
    else:
        return 2


def generate_accounts(num_accounts: int, regions: List[str], start_date: str,
                      seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    批量生成账户角色故事

    Args:
        num_accounts: 账户数量
        regions: 地区列表
        start_date: 起始日期
        seed: 随机种子（用于复现）

    Returns:
        账户角色故事列表
    """
    from datetime import datetime, timedelta

    # 设置随机种子
    if seed is not None:
        random.seed(seed)

    accounts = []
    start_dt = datetime.strptime(start_date, "%Y%m%d")

    for i in range(num_accounts):
        # 生成账户ID
        account_id = f"ACC_{i+1:05d}"

        # 随机生成姓名（简单实现）
        surnames = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
        names = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "洋"]
        account_name = random.choice(surnames) + random.choice(names)

        # 随机选择地区
        region = random.choice(regions)

        # 随机生成注册时间（start_date之前30-365天）
        days_before = random.randint(30, 365)
        sign_up_time = (start_dt - timedelta(days=days_before)).strftime("%Y-%m-%d")

        # 根据比例选择风险等级
        risk_level = select_risk_level()

        # 生成完整账户
        account = generate_account_with_template(
            account_id=account_id,
            account_name=account_name,
            region=region,
            sign_up_time=sign_up_time,
            risk_level=risk_level
        )

        accounts.append(account)

    return accounts


def save_accounts(accounts: List[Dict[str, Any]], filepath: str) -> None:
    """
    保存账户角色故事到 JSON 文件

    Args:
        accounts: 账户列表
        filepath: 保存路径
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def load_accounts(filepath: str) -> List[Dict[str, Any]]:
    """
    从 JSON 文件加载账户角色故事

    Args:
        filepath: 文件路径

    Returns:
        账户列表
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
