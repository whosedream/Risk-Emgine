"""
入口文件 - 多维行为日志数据生成
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 必须先加载 .env 文件，再导入其他模块
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

# 延迟导入，确保环境变量已加载
from script.generate import generate_data


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="多维行为日志数据生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py 20260601 20260630 ./data train 100
  python main.py 20260601 20260630 ./data train 100 --seed 42
  python main.py 20260601 20260630 ./data train 100 --load-stories stories.json
  python main.py 20260601 20260630 ./data train 100 --concurrency 10
        """
    )

    parser.add_argument("start_date", help="起始日期 (YYYYMMDD)")
    parser.add_argument("end_date", help="结束日期 (YYYYMMDD)")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("mode", choices=["train", "test"], help="模式: train(训练) / test(测试)")
    parser.add_argument("num_accounts", nargs="?", type=int, default=100,
                        help="生成账户数量 (默认: 100)")
    parser.add_argument("--min-records", type=int, default=20,
                        help="每个账户最小记录数 (默认: 20)")
    parser.add_argument("--max-records", type=int, default=50,
                        help="每个账户最大记录数 (默认: 50)")
    parser.add_argument("--seed", type=int, default=None,
                        help="随机种子（用于复现角色故事）")
    parser.add_argument("--load-stories", type=str, default=None,
                        help="从 JSON 文件加载角色故事")
    parser.add_argument("--save-stories", type=str, default=None,
                        help="保存角色故事到 JSON 文件")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="并发数 (默认: 5)")

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
            num_accounts=args.num_accounts,
            min_records_per_account=args.min_records,
            max_records_per_account=args.max_records,
            seed=args.seed,
            load_stories_path=args.load_stories,
            save_stories_path=args.save_stories,
            concurrency=args.concurrency
        )
        print(f"\n成功生成数据文件: {output_file}")
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
