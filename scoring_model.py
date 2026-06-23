"""
风险打分模型 — 加权求和 + 8 条规则增强，输出 0~100 风险评分

接收 extract_features() 的返回值作为输入，
综合各特征权重计算基础分，叠加 8 条规则增强后输出最终评分和风险等级。
"""
from __future__ import annotations


# ── 默认权重（可调） ──────────────────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "device_reuse_ratio": 0.25,
    "ip_change_freq": 0.20,
    "tx_freq": 0.20,
    "login_fail_ratio": 0.15,
    "amount_anomaly_score": 0.20,
}


def score_risk(
    features: dict[str, float],
    weights: dict[str, float] | None = None,
) -> dict[str, float | str]:
    """加权求和 + 规则增强，计算综合风险评分。

    Args:
        features: extract_features() 返回的特征 dict，
                  包含 device_reuse_ratio, ip_change_freq, tx_freq,
                  login_fail_ratio, amount_anomaly_score
        weights: 可选自定义权重 dict，键名与 features 一致。
                 默认使用 DEFAULT_WEIGHTS。

    Returns:
        {"score": float, "level": str, "level_range": str}
        - score: 0~100 范围内的风险评分
        - level: "LOW" / "MEDIUM" / "HIGH"
        - level_range: "0~30" / "31~70" / "71~100"
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # ── 加权求和 ──────────────────────────────────────────
    # tx_freq 需要归一化：min(1.0, tx_freq / 100)
    normalized_tx = min(1.0, features.get("tx_freq", 0.0) / 100.0)

    weighted_sum = (
        weights.get("device_reuse_ratio", 0.0) * features.get("device_reuse_ratio", 0.0)
        + weights.get("ip_change_freq", 0.0) * features.get("ip_change_freq", 0.0)
        + weights.get("tx_freq", 0.0) * normalized_tx
        + weights.get("login_fail_ratio", 0.0) * features.get("login_fail_ratio", 0.0)
        + weights.get("amount_anomaly_score", 0.0) * features.get("amount_anomaly_score", 0.0)
    )

    # 转为百分制
    score = weighted_sum * 100.0

    # ── 规则增强（加分项） ────────────────────────────────
    boost = 0.0

    # 规则1：设备复用率高 + 交易频率高
    if features.get("device_reuse_ratio", 0.0) > 0.9 and features.get("tx_freq", 0.0) > 50:
        boost += 10.0

    # 规则2：IP变更频繁 + 登录失败率高
    if features.get("ip_change_freq", 0.0) > 0.8 and features.get("login_fail_ratio", 0.0) > 0.5:
        boost += 10.0

    # 规则3：金额极端异常（低调大额欺诈）
    if features.get("amount_anomaly_score", 0.0) > 0.7:
        boost += 15.0

    # 规则4：暴力破解/撞库（登录失败占主导）
    if features.get("login_fail_ratio", 0.0) > 0.7:
        boost += 20.0

    # 规则5：设备共享（多账户共用设备，即使行为正常）
    if features.get("device_reuse_ratio", 0.0) > 0.2:
        boost += 19.0

    # 规则6：IP变更 + 金额异常（账户盗用：切换IP后大额交易）
    if features.get("ip_change_freq", 0.0) > 0.1 and features.get("amount_anomaly_score", 0.0) > 0.3:
        boost += 15.0

    # 规则7：设备复用 + 登录失败（设备农场撞库：共享设备上大量试密码）
    if features.get("device_reuse_ratio", 0.0) > 0.15 and features.get("login_fail_ratio", 0.0) > 0.3:
        boost += 15.0

    # 规则8：高频交易 + 金额异常（洗钱：短时间大量高额交易）
    if features.get("tx_freq", 0.0) > 10 and features.get("amount_anomaly_score", 0.0) > 0.3:
        boost += 15.0

    score += boost

    # ── 钳制到 0~100 ──────────────────────────────────────
    score = max(0.0, min(100.0, score))

    # ── 风险等级映射 ──────────────────────────────────────
    if score <= 30.0:
        level = "LOW"
        level_range = "0~30"
    elif score <= 70.0:
        level = "MEDIUM"
        level_range = "31~70"
    else:
        level = "HIGH"
        level_range = "71~100"

    return {
        "score": score,
        "level": level,
        "level_range": level_range,
    }
