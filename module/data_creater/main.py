"""
入口文件 - 多维行为日志数据生成
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from script.generate import generate_data


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="多维行为日志数据生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py 20260601 20260630 ./data train 100
  python main.py 20260601 20260630 ./data test --num_accounts 50
        """
    )

    parser.add_argument("start_date", help="起始日期 (YYYYMMDD)")
    parser.add_argument("end_date", help="结束日期 (YYYYMMDD)")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("mode", choices=["train", "test"], help="模式: train(训练) / test(测试)")
    parser.add_argument("num_accounts", nargs="?", type=int, default=100,
                        help="生成账户数量 (默认: 100)")

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    try:
        output_file = await generate_data(
            start_date=args.start_date,
            end_date=args.end_date,
            output_dir=args.output_dir,
            mode=args.mode,
            num_accounts=args.num_accounts
        )
        print(f"\n成功生成数据文件: {output_file}")
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
