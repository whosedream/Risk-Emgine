"""
主生成脚本 - 生成多维行为日志数据
"""

import csv
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.llm import call_llm_with_retry
from prompts.role_loader import generate_accounts
from prompts.behavior import BEHAVIOR_SYSTEM_PROMPT, get_behavior_prompt
from config.settings import (
    DEFAULT_NUM_ACCOUNTS,
    DATE_FORMAT,
    REGIONS,
    DATA_DIR
)

logger = logging.getLogger(__name__)


def validate_date(date_str: str) -> datetime:
    """验证并解析日期"""
    try:
        return datetime.strptime(date_str, DATE_FORMAT)
    except ValueError:
        raise ValueError(f"日期格式错误: {date_str}，应为 YYYYMMDD")


def validate_params(start_date: str, end_date: str, mode: str, num_accounts: int) -> None:
    """验证输入参数"""
    start = validate_date(start_date)
    end = validate_date(end_date)

    if end < start:
        raise ValueError(f"end_date ({end_date}) 必须 >= start_date ({start_date})")

    if mode not in ("train", "test"):
        raise ValueError(f"mode 必须为 train 或 test，当前: {mode}")

    if num_accounts <= 0:
        raise ValueError(f"num_accounts 必须 > 0，当前: {num_accounts}")


async def enhance_account_with_llm(account: dict) -> dict:
    """用 LLM 增强账户的表面细节

    LLM 生成的值会替换模板原值（不是新增字段）
    """
    prompt = f"""基于以下角色模板，生成该用户的表面细节信息。

角色模板：
{json.dumps(account, ensure_ascii=False, indent=2)}

请生成以下字段（这些字段的值将替换模板原值）：
1. account_name: 中文姓名（随机生成）
2. device_info: 具体设备型号（保留模板的设备类型，但指定具体型号和指纹）
3. behavior_pattern: 更具体的行为描述（保留模板的核心特征，但增加细节）

以 JSON 格式返回，只包含上述 3 个字段。"""

    try:
        result = await call_llm_with_retry(prompt, parse_json=True, max_retries=3)
        account["account_name"] = result.get("account_name", account["account_name"])
        account["device_info"] = result.get("device_info", account["device_info"])
        account["behavior_pattern"] = result.get("behavior_pattern", account["behavior_pattern"])
    except Exception as e:
        logger.warning(f"LLM 增强失败，使用模板默认值: {e}")

    return account


async def generate_behavior_data(role_story: Dict, start_date: str, end_date: str, mode: str) -> List[Dict]:
    """为单个用户生成行为数据"""
    prompt = get_behavior_prompt(role_story, start_date, end_date, mode)
    response = await call_llm_with_retry(prompt, BEHAVIOR_SYSTEM_PROMPT, parse_json=True, max_retries=3)

    if isinstance(response, list):
        return response
    elif isinstance(response, dict) and "behaviors" in response:
        return response["behaviors"]
    else:
        raise ValueError(f"Unexpected response format: {response}")


async def generate_data(start_date: str, end_date: str, output_dir: str, mode: str, num_accounts: int = DEFAULT_NUM_ACCOUNTS) -> str:
    """
    生成多维行为日志数据

    Args:
        start_date: 起始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        output_dir: 输出目录
        mode: 模式 (train/test)
        num_accounts: 生成账户数量

    Returns:
        输出文件路径
    """
    # 验证参数
    validate_params(start_date, end_date, mode, num_accounts)

    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 输出文件路径
    output_file = output_path / f"{start_date}_{end_date}_risk.csv"

    print(f"开始生成数据...")
    print(f"  时间范围: {start_date} - {end_date}")
    print(f"  模式: {mode}")
    print(f"  账户数量: {num_accounts}")
    print(f"  输出文件: {output_file}")

    # 1. 使用模板生成账户（同步，无 LLM 调用）
    print("\n[1/4] 生成角色故事（模板）...")
    role_stories = generate_accounts(num_accounts, REGIONS, start_date)
    print(f"  已生成 {len(role_stories)} 个角色故事")

    # 2. LLM 增强每个账户（顺序执行，避免 429 速率限制）
    print("\n[2/4] 增强账户细节（LLM）...")
    for i, account in enumerate(role_stories):
        role_stories[i] = await enhance_account_with_llm(account)
        if (i + 1) % 10 == 0:
            print(f"  已增强 {i+1}/{len(role_stories)} 个账户")
    print(f"  已增强 {len(role_stories)} 个账户")

    # 3. 生成行为数据
    print("\n[3/4] 生成行为数据...")
    all_records = []

    for i, story in enumerate(role_stories):
        print(f"  处理账户 {i+1}/{len(role_stories)}: {story.get('account_name', 'Unknown')}")

        try:
            behaviors = await generate_behavior_data(story, start_date, end_date, mode)

            # 为每条行为记录添加账户信息
            for behavior in behaviors:
                record = {
                    "account_id": story["account_id"],
                    "account_name": story["account_name"],
                    "region": story["region"],
                    "sign_up_time": story["sign_up_time"],
                    "machine": story.get("device_info", ""),
                    **behavior
                }

                # 训练模式添加标签
                if mode == "train":
                    record["label"] = story.get("risk_level", 0)

                all_records.append(record)
        except Exception as e:
            print(f"    警告: 生成失败 - {e}")
            continue

    print(f"  已生成 {len(all_records)} 条行为记录")

    # 4. 写入 CSV
    print("\n[4/4] 写入 CSV 文件...")

    if not all_records:
        raise ValueError("没有生成任何数据")

    # 定义 CSV 列
    columns = [
        "account_id", "account_name", "region", "pub_time", "ip_address",
        "type", "machine", "behavior_type", "behavior_period_time",
        "behavior_log", "money_size", "sign_up_time"
    ]

    if mode == "train":
        columns.append("label")

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n✓ 数据生成完成！")
    print(f"  输出文件: {output_file}")
    print(f"  总记录数: {len(all_records)}")

    return str(output_file)


if __name__ == "__main__":
    import sys as _sys

    if len(_sys.argv) < 5:
        print("用法: python generate.py <start_date> <end_date> <output_dir> <mode> [num_accounts]")
        _sys.exit(1)

    start_date = _sys.argv[1]
    end_date = _sys.argv[2]
    output_dir = _sys.argv[3]
    mode = _sys.argv[4]
    num_accounts = int(_sys.argv[5]) if len(_sys.argv) > 5 else DEFAULT_NUM_ACCOUNTS

    asyncio.run(generate_data(start_date, end_date, output_dir, mode, num_accounts))
