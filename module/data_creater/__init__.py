"""
多维行为日志数据生成模块

对外接口：
    generate_data(start_date, end_date, output_dir, mode, num_accounts)

使用示例：
    from data_creater import generate_data
    generate_data("20260601", "20260630", "./data", "train", 100)
"""

from .script.generate import generate_data

__all__ = ["generate_data"]
__version__ = "1.0.0"
