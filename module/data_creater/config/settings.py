"""
配置文件 - 数据生成模块
"""

import os
from pathlib import Path

# 项目路径
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR.parent.parent / "data"

# API 配置
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://token-plan-cn.xiaomimimo.com/anthropic")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
MODEL = os.getenv("MODEL", "mimo-v2.5")

# 数据生成配置
DEFAULT_NUM_ACCOUNTS = 100
DATE_FORMAT = "%Y%m%d"

# 行为类型
BEHAVIOR_TYPES = ["login", "register", "transaction", "browse", "search", "comment"]

# 风险等级
RISK_LEVELS = {
    0: "低风险",
    1: "中风险",
    2: "高风险"
}

# 地区列表
REGIONS = [
    "北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京",
    "西安", "重庆", "天津", "苏州", "长沙", "郑州", "青岛"
]
