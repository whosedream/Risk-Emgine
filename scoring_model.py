"""
风险打分模型 — 加权求和 + 16 条规则增强 + 可选 ML 混合评分

接收 extract_features() 的返回值（17个特征）作为输入，
综合各特征权重计算基础分，叠加 16 条规则增强后输出最终评分和风险等级。

新增: score_risk_hybrid() — 规则模型 + RandomForest 加权融合
"""
from __future__ import annotations

import os
import numpy as np

# ── ML 模型路径 ────────────────────────────────────────
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "data", "model")
_SCALER_PATH = os.path.join(_MODEL_DIR, "scaler.pkl")
_RF_PATH = os.path.join(_MODEL_DIR, "random_forest.pkl")
_XGB_PATH = os.path.join(_MODEL_DIR, "xgboost.pkl")
_ENS_PATH = os.path.join(_MODEL_DIR, "ensemble.pkl")

# 懒加载缓存
_ml_scaler = None
_ml_model = None


def _get_best_model_path() -> str:
    """返回可用的最佳模型路径（Ensemble > XGBoost > RandomForest）。"""
    for path in [_ENS_PATH, _XGB_PATH, _RF_PATH]:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"ML 模型未找到。请先运行 train_ml_model.py 训练并保存模型。"
    )

# 特征顺序（必须与训练时一致）
_ML_FEATURE_ORDER = [
    "device_reuse_ratio", "ip_change_freq", "tx_freq",
    "login_fail_ratio", "amount_anomaly_score",
    "behavior_time_anomaly", "multi_region_risk",
    "tx_velocity_5min", "tx_velocity_1h",
    "device_switch_24h", "ip_switch_24h",
    "tx_interval_mean_sec", "tx_burst_ratio",
    "amount_user_deviation", "amount_user_max_ratio",
    "night_tx_ratio", "odd_hour_tx_ratio",
]


def _load_ml_model():
    """懒加载 ML 模型 + 标准化器（首次调用时加载，自动选择最佳可用模型）。"""
    global _ml_scaler, _ml_model
    if _ml_model is None:
        import joblib
        best_path = _get_best_model_path()
        _ml_scaler = joblib.load(_SCALER_PATH)
        _ml_model = joblib.load(best_path)
    return _ml_scaler, _ml_model


# ── 默认权重（可调，总和=1.0）v1.2.0: 15 特征 ─────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "device_reuse_ratio":      0.10,
    "ip_change_freq":          0.08,
    "tx_freq":                 0.08,
    "login_fail_ratio":        0.08,
    "amount_anomaly_score":    0.10,
    "behavior_time_anomaly":   0.07,
    "multi_region_risk":       0.05,
    "tx_velocity_5min":        0.08,
    "tx_velocity_1h":          0.08,
    "device_switch_24h":       0.04,
    "ip_switch_24h":           0.05,
    "tx_interval_mean_sec":    0.04,
    "tx_burst_ratio":          0.04,
    "amount_user_deviation":   0.03,
    "amount_user_max_ratio":   0.03,
    "night_tx_ratio":          0.03,
    "odd_hour_tx_ratio":       0.02,
}


def score_risk(
    features: dict[str, float],
    weights: dict[str, float] | None = None,
) -> dict[str, float | str]:
    """加权求和 + 规则增强，计算综合风险评分。

    Args:
        features: extract_features() 返回的特征 dict（17 维）
        weights: 可选自定义权重 dict，键名与 features 一致。
                 默认使用 DEFAULT_WEIGHTS（17 维，总和=1.0）。

    Returns:
        {"score": float, "level": str, "level_range": str}
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # ── 加权求和 ──────────────────────────────────────────
    # tx_freq 需要归一化：min(1.0, tx_freq / 100)
    normalized_tx = min(1.0, features.get("tx_freq", 0.0) / 100.0)

    # velocity 特征的归一化
    v5   = min(1.0, features.get("tx_velocity_5min", 0.0) / 10.0)
    v1h  = min(1.0, features.get("tx_velocity_1h", 0.0) / 30.0)
    ds   = min(1.0, features.get("device_switch_24h", 0.0) / 5.0)
    isw  = min(1.0, features.get("ip_switch_24h", 0.0) / 10.0)
    # interval: 间隔→归一化 (反向，越低越危险)。
    # 当 tx_freq=0 时 interval=0 无意义，应贡献 0
    iv_raw = features.get("tx_interval_mean_sec", 3600.0)
    iv_n = 0.0 if iv_raw <= 0 else 1.0 - min(1.0, iv_raw / 3600.0)
    br   = features.get("tx_burst_ratio", 0.0)  # already 0~1
    # amount baseline
    aud  = min(1.0, features.get("amount_user_deviation", 0.0) / 5.0)
    amr  = min(1.0, features.get("amount_user_max_ratio", 0.0) / 10.0)
    # cyclic time: already 0~1 ratios
    nt   = features.get("night_tx_ratio", 0.0)
    ot   = features.get("odd_hour_tx_ratio", 0.0)

    weighted_sum = (
        weights.get("device_reuse_ratio", 0.0)     * features.get("device_reuse_ratio", 0.0)
        + weights.get("ip_change_freq", 0.0)       * features.get("ip_change_freq", 0.0)
        + weights.get("tx_freq", 0.0)              * normalized_tx
        + weights.get("login_fail_ratio", 0.0)     * features.get("login_fail_ratio", 0.0)
        + weights.get("amount_anomaly_score", 0.0) * features.get("amount_anomaly_score", 0.0)
        + weights.get("behavior_time_anomaly", 0.0)* features.get("behavior_time_anomaly", 0.0)
        + weights.get("multi_region_risk", 0.0)    * features.get("multi_region_risk", 0.0)
        + weights.get("tx_velocity_5min", 0.0)     * v5
        + weights.get("tx_velocity_1h", 0.0)       * v1h
        + weights.get("device_switch_24h", 0.0)    * ds
        + weights.get("ip_switch_24h", 0.0)        * isw
        + weights.get("tx_interval_mean_sec", 0.0) * iv_n
        + weights.get("tx_burst_ratio", 0.0)       * br
        + weights.get("amount_user_deviation", 0.0)* aud
        + weights.get("amount_user_max_ratio", 0.0)* amr
        + weights.get("night_tx_ratio", 0.0)       * nt
        + weights.get("odd_hour_tx_ratio", 0.0)    * ot
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

    # 规则9：自动化脚本 — 行为极快 + 交易频繁（机器人跑量）
    if features.get("behavior_time_anomaly", 0.0) > 0.3 and features.get("tx_freq", 0.0) > 20:
        boost += 15.0

    # 规则10：多地区异常 — 同一账户在不同地区活动（物理不可能）
    if features.get("multi_region_risk", 0.0) > 0:
        boost += 12.0

    # 规则11：交易爆发 — 5分钟内超5笔交易（卡片测试/盗刷洗钱）
    if features.get("tx_velocity_5min", 0.0) > 5:
        boost += 12.0

    # 规则12：高频交易 + 设备/IP 频繁切换（账户接管后快速变现）
    if features.get("tx_velocity_1h", 0.0) > 15 and \
       (features.get("device_switch_24h", 0.0) > 3 or features.get("ip_switch_24h", 0.0) > 5):
        boost += 15.0

    # 规则13：交易间隔极短 — 平均<30s = 自动化脚本
    if features.get("tx_interval_mean_sec", 999.0) < 30.0 and features.get("tx_freq", 0.0) > 5:
        boost += 10.0

    # 规则14：单笔超大金额 — 用户最大交易 / 用户均值 > 10
    if features.get("amount_user_max_ratio", 0.0) > 10.0:
        boost += 10.0

    # 规则15：交易突发 — 60s 内连续交易 >50% + 高频交易
    if features.get("tx_burst_ratio", 0.0) > 0.5 and features.get("tx_freq", 0.0) > 10:
        boost += 10.0

    # 规则16：凌晨交易 — 1am-5am 交易占比 >30%（正常用户此时休息）
    if features.get("night_tx_ratio", 0.0) > 0.3:
        boost += 8.0

    score += boost

    # ── 钳制到 0~100 ──────────────────────────────────────
    score = max(0.0, min(100.0, score))

    # ── 风险等级映射 (v1.2.0 校准) ──────────────────────────
    # 基于验证集 PR 曲线优化，HIGH 门槛从 71→55
    if score <= 30.0:
        level = "LOW"
        level_range = "0~30"
    elif score <= 55.0:
        level = "MEDIUM"
        level_range = "31~55"
    else:
        level = "HIGH"
        level_range = "56~100"

    return {
        "score": score,
        "level": level,
        "level_range": level_range,
    }


def score_risk_hybrid(
    features: dict[str, float],
    weights: dict[str, float] | None = None,
    alpha: float = 0.2,
) -> dict[str, float | str]:
    """规则模型 + RandomForest 加权融合评分。

    最终分 = α × 规则分 + (1-α) × ML概率分

    Args:
        features: extract_features() 返回的特征 dict（17 维）
        weights: 可选自定义权重，传给 score_risk()
        alpha: 规则模型权重 (0~1)，默认 0.2（20%规则 + 80%ML）。
               alpha=1.0 退化为纯规则模型，alpha=0.0 退化为纯 ML。

    Returns:
        {"score": float, "level": str, "level_range": str,
         "rule_score": float, "ml_score": float}
    """
    # 1. 规则分
    rule_result = score_risk(features, weights)
    rule_score = rule_result["score"]

    # 2. ML 概率分
    scaler, model = _load_ml_model()
    X = np.array([[features.get(k, 0.0) for k in _ML_FEATURE_ORDER]])
    X_scaled = scaler.transform(X)
    proba = model.predict_proba(X_scaled)[0]  # [P(LOW), P(MEDIUM), P(HIGH)]

    # 概率映射到 0-100: P(MEDIUM)*50 + P(HIGH)*100
    ml_score = float(proba[1] * 50.0 + proba[2] * 100.0)

    # 3. 加权融合
    score = alpha * rule_score + (1.0 - alpha) * ml_score
    score = max(0.0, min(100.0, score))

    # 4. 等级映射
    if score <= 30.0:
        level, level_range = "LOW", "0~30"
    elif score <= 55.0:
        level, level_range = "MEDIUM", "31~55"
    else:
        level, level_range = "HIGH", "56~100"

    return {
        "score": score,
        "level": level,
        "level_range": level_range,
        "rule_score": rule_score,
        "ml_score": ml_score,
    }
