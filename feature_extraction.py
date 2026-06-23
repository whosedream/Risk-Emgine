"""
特征提取模块 — 从行为日志 CSV 计算反欺诈特征向量

输入: CSV 行为日志（字段: user_id, event_type, device_id, ip_address, timestamp, amount）
输出: 5 个特征指标的 dict[str, float]

@data: 由调用方通过 csv_path 参数传入
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def _load_and_validate(csv_path: str) -> tuple[pd.DataFrame, bool]:
    """读取并校验 CSV，返回 (DataFrame, has_amount)。

    Args:
        csv_path: 行为日志 CSV 文件路径

    Returns:
        (df, has_amount) — df 已解析 timestamp 列

    Raises:
        ValueError: CSV 无法读取、为空、或缺少必填字段时抛出
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        raise ValueError(f"无法读取CSV文件: {csv_path}")

    if df.empty or len(df) == 0:
        raise ValueError(f"CSV文件为空或无数据行: {csv_path}")

    # 确保必要字段存在
    required_cols = {"user_id", "event_type", "device_id", "ip_address", "timestamp"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"CSV缺少必填字段: {missing_cols}")

    # 检查 amount 字段
    has_amount = "amount" in df.columns

    # 解析时间戳
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    return df, has_amount


def extract_features(csv_path: str) -> dict[str, float]:
    """从行为日志 CSV 提取欺诈特征向量（聚合模式，所有用户取平均）。

    Args:
        csv_path: 行为日志 CSV 文件路径

    Returns:
        包含 5 个特征键名的 dict:
        - device_reuse_ratio (0.0~1.0): 设备复用率
        - ip_change_freq (0.0~1.0): IP 变更频率（归一化）
        - tx_freq (>=0.0): 24h 内交易频率（原始计数均值）
        - login_fail_ratio (0.0~1.0): 登录失败率
        - amount_anomaly_score (0.0~1.0): 交易金额异常分数
    """
    df, has_amount = _load_and_validate(csv_path)

    # ── 基础统计 ──────────────────────────────────────────
    total_users = df["user_id"].nunique()
    if total_users == 0:
        raise ValueError("CSV数据中无有效用户")

    # ── 1. device_reuse_ratio ─────────────────────────────
    device_reuse_ratio = _calc_device_reuse_ratio(df, total_users)

    # ── 2. ip_change_freq ────────────────────────────────
    ip_change_freq = _calc_ip_change_freq(df)

    # ── 3. tx_freq ────────────────────────────────────────
    tx_freq = _calc_tx_freq(df)

    # ── 4. login_fail_ratio ───────────────────────────────
    login_fail_ratio = _calc_login_fail_ratio(df)

    # ── 5. amount_anomaly_score ───────────────────────────
    amount_anomaly_score = _calc_amount_anomaly_score(df, has_amount)

    return {
        "device_reuse_ratio": device_reuse_ratio,
        "ip_change_freq": ip_change_freq,
        "tx_freq": tx_freq,
        "login_fail_ratio": login_fail_ratio,
        "amount_anomaly_score": amount_anomaly_score,
    }


def extract_features_per_user(csv_path: str) -> dict[str, dict[str, float]]:
    """从行为日志 CSV 提取每个用户的独立欺诈特征向量。

    与 extract_features() 不同，此函数为每个用户独立计算特征，
    而不是将所有用户取平均。适用于需要识别个体欺诈用户的场景。

    Args:
        csv_path: 行为日志 CSV 文件路径

    Returns:
        {user_id: {feature_name: value}}
        每个用户的特征 dict 包含 5 个键:
        - device_reuse_ratio (0.0~1.0)
        - ip_change_freq (0.0~1.0)
        - tx_freq (>=0.0)
        - login_fail_ratio (0.0~1.0)
        - amount_anomaly_score (0.0~1.0)

    Raises:
        ValueError: CSV 无法读取、为空、或缺少必填字段时抛出
    """
    df, has_amount = _load_and_validate(csv_path)

    total_users = df["user_id"].nunique()
    if total_users == 0:
        raise ValueError("CSV数据中无有效用户")

    all_users = sorted(df["user_id"].unique())

    # ── 1. device_reuse_ratio per user ────────────────────
    device_user_counts = df.groupby("device_id")["user_id"].nunique()
    user_devices = df.groupby("user_id")["device_id"].apply(set)
    device_reuse: dict[str, float] = {}
    for user in all_users:
        devices = user_devices.get(user, set())
        max_shared = max(
            (device_user_counts.get(d, 0) for d in devices),
            default=0,
        )
        device_reuse[user] = max_shared / total_users

    # ── 2. ip_change_freq per user ───────────────────────
    total_ips = df["ip_address"].nunique()
    user_ip_counts = df.groupby("user_id")["ip_address"].nunique()
    ip_change: dict[str, float] = {}
    for user in all_users:
        if total_ips > 0:
            ip_change[user] = user_ip_counts.get(user, 0) / total_ips
        else:
            ip_change[user] = 0.0

    # ── 3. tx_freq per user ───────────────────────────────
    tx_df = df[df["event_type"] == "transaction"]
    user_tx_counts = tx_df.groupby("user_id").size()
    tx_freq_per_user: dict[str, float] = {
        u: float(user_tx_counts.get(u, 0)) for u in all_users
    }

    # ── 4. login_fail_ratio per user ──────────────────────
    login_mask = df["event_type"].isin(["login", "login_fail"])
    login_df = df[login_mask]
    login_fail_counts = (
        login_df[login_df["event_type"] == "login_fail"]
        .groupby("user_id")
        .size()
    )
    total_login_counts = login_df.groupby("user_id").size()
    login_fail_per_user: dict[str, float] = {}
    for user in all_users:
        fails = login_fail_counts.get(user, 0)
        total = total_login_counts.get(user, 0)
        login_fail_per_user[user] = (fails / total) if total > 0 else 0.0

    # ── 5. amount_anomaly_score per user ──────────────────
    # 全局计算 MAD 稳健 Z-score，每个用户取其交易 anomaly 均值
    amount_anomaly_per_user: dict[str, float] = {u: 0.0 for u in all_users}
    if has_amount:
        tx_amount_mask = (df["event_type"] == "transaction") & df["amount"].notna()
        tx_amount_df = df[tx_amount_mask]
        if not tx_amount_df.empty and len(tx_amount_df) >= 2:
            amounts = tx_amount_df["amount"].astype(float)
            median_val = amounts.median()
            mad_val = np.median(np.abs(amounts - median_val)) * 1.4826
            if mad_val > 0 and not pd.isna(mad_val):
                robust_z_scores = np.abs((amounts - median_val) / mad_val)
                anomaly_scores_arr = np.minimum(1.0, robust_z_scores / 3.0)
                tx_amount_df = tx_amount_df.copy()
                tx_amount_df["_anomaly"] = anomaly_scores_arr.values
                user_anomaly_avg = tx_amount_df.groupby("user_id")["_anomaly"].mean()
                for user in all_users:
                    if user in user_anomaly_avg.index:
                        amount_anomaly_per_user[user] = float(user_anomaly_avg[user])

    # ── 组装返回 ──────────────────────────────────────────
    result: dict[str, dict[str, float]] = {}
    for user in all_users:
        result[user] = {
            "device_reuse_ratio": device_reuse[user],
            "ip_change_freq": ip_change[user],
            "tx_freq": tx_freq_per_user[user],
            "login_fail_ratio": login_fail_per_user[user],
            "amount_anomaly_score": amount_anomaly_per_user[user],
        }

    return result


# ── 各特征计算函数 ────────────────────────────────────────


def _calc_device_reuse_ratio(df: pd.DataFrame, total_users: int) -> float:
    """计算设备复用率。

    对每个用户，取其使用过的设备中被最多不同用户共享的设备复用率
    （该设备关联的不同 user_id 数 / 总 user_id 数），
    然后取所有用户的平均值。

    Args:
        df: 行为日志 DataFrame
        total_users: 总不同 user_id 数

    Returns:
        device_reuse_ratio (0.0~1.0)
    """
    # 每个设备关联的不同用户数
    device_user_counts = df.groupby("device_id")["user_id"].nunique()

    # 每个用户使用的设备集合
    user_devices = df.groupby("user_id")["device_id"].apply(set)

    ratios: list[float] = []
    for _user, devices in user_devices.items():
        # 该用户使用的所有设备中，被最多用户共享的那个
        max_shared = max(
            (device_user_counts.get(d, 0) for d in devices),
            default=0,
        )
        ratios.append(max_shared / total_users)

    return float(np.mean(ratios)) if ratios else 0.0


def _calc_ip_change_freq(df: pd.DataFrame) -> float:
    """计算 IP 变更频率。

    统计每个 user_id 在 24h 内使用的不同 IP 数，
    除以数据集中总不同 IP 数归一化到 0.0~1.0，
    取所有用户平均值。

    Args:
        df: 行为日志 DataFrame

    Returns:
        ip_change_freq (0.0~1.0)
    """
    total_ips = df["ip_address"].nunique()
    if total_ips == 0:
        return 0.0

    # 每个用户使用的不同 IP 数
    user_ip_counts = df.groupby("user_id")["ip_address"].nunique()

    # 归一化并取平均
    normalized = user_ip_counts / total_ips
    return float(normalized.mean())


def _calc_tx_freq(df: pd.DataFrame) -> float:
    """计算交易频率。

    统计每个 user_id 的 event_type == "transaction" 事件数，
    取所有用户的平均值（原始计数，不归一化）。

    Args:
        df: 行为日志 DataFrame

    Returns:
        tx_freq (>=0.0)
    """
    tx_df = df[df["event_type"] == "transaction"]
    if tx_df.empty:
        return 0.0

    # 每个用户的交易次数
    user_tx_counts = tx_df.groupby("user_id").size()

    # 所有用户的平均值（包含没有交易记录的用户，计为 0）
    all_users = df["user_id"].unique()
    tx_per_user = {u: 0 for u in all_users}
    for user, count in user_tx_counts.items():
        tx_per_user[user] = count

    return float(np.mean(list(tx_per_user.values())))


def _calc_login_fail_ratio(df: pd.DataFrame) -> float:
    """计算登录失败率。

    对每个 user_id 计算 login_fail 次数 / (login 成功 + login_fail 总次数)，
    取所有用户的平均值。
    无 login 或 login_fail 事件的用户计为 0.0。

    Args:
        df: 行为日志 DataFrame

    Returns:
        login_fail_ratio (0.0~1.0)
    """
    # 筛选登录相关事件
    login_mask = df["event_type"].isin(["login", "login_fail"])
    login_df = df[login_mask]

    if login_df.empty:
        return 0.0

    # 统计每个用户的 login_fail 和总登录事件
    login_fail_counts = (
        login_df[login_df["event_type"] == "login_fail"]
        .groupby("user_id")
        .size()
    )
    total_login_counts = login_df.groupby("user_id").size()

    # 计算每个用户的失败率
    all_users = df["user_id"].unique()
    ratios: list[float] = []
    for user in all_users:
        fails = login_fail_counts.get(user, 0)
        total = total_login_counts.get(user, 0)
        if total > 0:
            ratios.append(fails / total)
        else:
            ratios.append(0.0)

    return float(np.mean(ratios)) if ratios else 0.0


def _calc_amount_anomaly_score(df: pd.DataFrame, has_amount: bool) -> float:
    """计算金额异常分数。

    基于 MAD 稳健 Z-score（中位数 + 中位数绝对偏差）计算金额异常度，
    抵抗极端值对统计基准的遮蔽效应，映射到 0.0~1.0 范围。
    常量 1.4826 使 MAD 在正态分布下等价于标准差。
    |robust_z| >= 3 时得分趋于 1.0。

    Args:
        df: 行为日志 DataFrame
        has_amount: CSV 是否包含 amount 字段

    Returns:
        amount_anomaly_score (0.0~1.0)
    """
    if not has_amount:
        return 0.0

    # 筛选有效交易记录（有金额的 transaction 事件）
    tx_mask = (df["event_type"] == "transaction") & df["amount"].notna()
    tx_df = df[tx_mask]

    if tx_df.empty or len(tx_df) < 2:
        return 0.0

    amounts = tx_df["amount"].astype(float)

    # 使用中位数和 MAD 进行稳健估计，抵抗极端值遮蔽效应
    median_val = amounts.median()
    # MAD = median(|x - median|), 常量 1.4826 使其在正态分布下等价于标准差
    mad_val = np.median(np.abs(amounts - median_val)) * 1.4826
    if mad_val == 0 or pd.isna(mad_val):
        return 0.0

    # 计算每个交易金额的稳健 Z-score，取均值作为整体异常度
    robust_z_scores = np.abs((amounts - median_val) / mad_val)

    # 稳健 Z-score 映射到 0.0~1.0：使用 min(1.0, |robust_z| / 3.0)
    # |robust_z|=2 → 0.667, |robust_z|=3 → 1.0
    anomaly_scores = np.minimum(1.0, robust_z_scores / 3.0)
    return float(anomaly_scores.mean())
