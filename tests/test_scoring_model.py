"""
scoring_model 模块测试

测试 score_risk() 函数的评分逻辑。
覆盖正常评分、边界值、规则增强、等级映射等场景。
"""
import pytest
from scoring_model import score_risk


# ── 辅助函数 ──────────────────────────────────────────────

def _make_features(
    device_reuse_ratio: float = 0.0,
    ip_change_freq: float = 0.0,
    tx_freq: float = 0.0,
    login_fail_ratio: float = 0.0,
    amount_anomaly_score: float = 0.0,
) -> dict[str, float]:
    return {
        "device_reuse_ratio": device_reuse_ratio,
        "ip_change_freq": ip_change_freq,
        "tx_freq": tx_freq,
        "login_fail_ratio": login_fail_ratio,
        "amount_anomaly_score": amount_anomaly_score,
    }


# ── 基础评分测试 ──────────────────────────────────────────

def test_score_all_zero():
    """测试全零特征：分数应为 0"""
    result = score_risk(_make_features())
    assert result["score"] == pytest.approx(0.0)
    assert result["level"] == "LOW"
    assert result["level_range"] == "0~30"


def test_score_all_one():
    """
    测试全1特征（tx_freq归一化后为1.0）：
    加权求和 = 0.25 + 0.20 + 0.20 + 0.15 + 0.20 = 1.0 -> 100分
    """
    result = score_risk(_make_features(
        device_reuse_ratio=1.0,
        ip_change_freq=1.0,
        tx_freq=100.0,  # 归一化后 = 1.0
        login_fail_ratio=1.0,
        amount_anomaly_score=1.0,
    ))
    assert result["score"] == pytest.approx(100.0)
    assert result["level"] == "HIGH"
    assert result["level_range"] == "71~100"


def test_score_mid_range():
    """
    测试中等风险场景：
    device_reuse=0.5, ip_change=0.5, tx_freq=50(norm=0.5),
    login_fail=0.5, amount_anomaly=0.5
    = 0.25*0.5 + 0.20*0.5 + 0.20*0.5 + 0.15*0.5 + 0.20*0.5
    = (0.25+0.20+0.20+0.15+0.20) * 0.5 = 1.0 * 0.5 = 50
    规则5(+19)、规则6(+15)、规则7(+15)、规则8(+15)触发，总计 +64 → 100 钳制
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.5,
        ip_change_freq=0.5,
        tx_freq=50.0,
        login_fail_ratio=0.5,
        amount_anomaly_score=0.5,
    ))
    assert result["score"] == pytest.approx(100.0)
    assert result["level"] == "HIGH"
    assert result["level_range"] == "71~100"


# ── 规则增强测试 ──────────────────────────────────────────

def test_rule_boost_device_tx():
    """
    规则增强：device_reuse_ratio > 0.9 且 tx_freq > 50，额外 +10 分
    同时 device_reuse_ratio > 0.2 触发规则5，额外 +19 分
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.95,  # > 0.9
        tx_freq=60.0,             # > 50
        ip_change_freq=0.0,
        login_fail_ratio=0.0,
        amount_anomaly_score=0.0,
    ))
    # 基础分: 0.25*0.95 + 0.20*0.0 + 0.20*min(1, 60/100) + 0.15*0.0 + 0.20*0.0
    # = 0.2375 + 0.0 + 0.12 + 0.0 + 0.0 = 0.3575 -> 35.75
    # 规则1 +10 + 规则5 +19 = +29
    expected_base = (0.25 * 0.95 + 0.20 * 0.0 + 0.20 * min(1.0, 60.0 / 100.0) + 0.15 * 0.0 + 0.20 * 0.0) * 100
    expected = min(100.0, expected_base + 29.0)
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_ip_login():
    """
    规则增强：ip_change_freq > 0.8 且 login_fail_ratio > 0.5，额外 +10 分
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.0,
        tx_freq=0.0,
        ip_change_freq=0.85,      # > 0.8
        login_fail_ratio=0.6,     # > 0.5
        amount_anomaly_score=0.0,
    ))
    expected_base = (0.25 * 0.0 + 0.20 * 0.85 + 0.20 * 0.0 + 0.15 * 0.6 + 0.20 * 0.0) * 100
    expected = min(100.0, expected_base + 10.0)
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_both():
    """
    两个规则同时触发：额外 +20 分
    同时 device_reuse_ratio > 0.2 触发规则5，额外 +19 分
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.95,  # > 0.9
        tx_freq=60.0,             # > 50
        ip_change_freq=0.85,      # > 0.8
        login_fail_ratio=0.6,     # > 0.5
        amount_anomaly_score=0.0,
    ))
    expected_base = (
        0.25 * 0.95 + 0.20 * 0.85 + 0.20 * min(1.0, 60.0 / 100.0) + 0.15 * 0.6 + 0.20 * 0.0
    ) * 100
    expected = min(100.0, expected_base + 39.0)
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_edge_boundaries():
    """
    规则1-4在边界值不触发。
    device_reuse_ratio=0.9（等于0.9，规则1不触发，但 > 0.2，规则5触发 +19，
      且 > 0.15，规则7触发 +15）
    ip_change_freq=0.8（等于0.8，规则2不触发）
    login_fail_ratio=0.5（等于0.5，但 > 0.3，与 device_reuse 组合触发规则7）
    amount_anomaly_score=0.0（规则6/8不触发）
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.9,   # = 0.9，规则1不触发；但 > 0.2/0.15，触发规则5/7
        tx_freq=50.0,             # = 50，规则1不触发
        ip_change_freq=0.8,       # = 0.8，规则2不触发
        login_fail_ratio=0.5,     # = 0.5，规则2/4不触发；触发规则7
        amount_anomaly_score=0.0,
    ))
    expected_base = (
        0.25 * 0.9 + 0.20 * 0.8 + 0.20 * min(1.0, 50.0 / 100.0) + 0.15 * 0.5 + 0.20 * 0.0
    ) * 100
    # 规则5 +19 + 规则7 +15 = +34
    assert result["score"] == pytest.approx(expected_base + 34.0)


def test_rule_boost_amount_only():
    """
    规则增强：amount_anomaly_score > 0.7，额外 +15 分
    仅 amount_anomaly_score=0.8，其余为 0
    """
    result = score_risk(_make_features(
        amount_anomaly_score=0.8,  # > 0.7
    ))
    # 基础分：0.20 * 0.8 * 100 = 16.0
    # +15 = 31.0
    expected_base = 0.20 * 0.8 * 100.0
    expected = min(100.0, expected_base + 15.0)
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_login_fail_only():
    """
    规则增强：login_fail_ratio > 0.7，额外 +20 分
    仅 login_fail_ratio=0.8，其余为 0
    """
    result = score_risk(_make_features(
        login_fail_ratio=0.8,  # > 0.7
    ))
    # 基础分：0.15 * 0.8 * 100 = 12.0
    # +20 = 32.0
    expected_base = 0.15 * 0.8 * 100.0
    expected = min(100.0, expected_base + 20.0)
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_device_reuse_only():
    """
    规则增强：device_reuse_ratio > 0.2，额外 +19 分
    仅 device_reuse_ratio=0.3，其余为 0
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.3,  # > 0.2
    ))
    # 基础分：0.25 * 0.3 * 100 = 7.5
    # +19 = 26.5
    expected_base = 0.25 * 0.3 * 100.0
    expected = min(100.0, expected_base + 19.0)
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_ip_amount():
    """
    规则6：ip_change_freq > 0.1 且 amount_anomaly_score > 0.3，额外 +15 分
    ip_change=0.2, amount=0.5，其余为 0
    """
    result = score_risk(_make_features(
        ip_change_freq=0.2,       # > 0.1
        amount_anomaly_score=0.5, # > 0.3
    ))
    # 基础分: 0.25*0 + 0.20*0.2 + 0.20*0 + 0.15*0 + 0.20*0.5 = 0.04 + 0.10 = 0.14 → 14.0
    # +15 = 29.0
    expected_base = (0.20 * 0.2 + 0.20 * 0.5) * 100.0
    expected = expected_base + 15.0
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_device_login():
    """
    规则7：device_reuse_ratio > 0.15 且 login_fail_ratio > 0.3，额外 +15 分
    device_reuse=0.2, login_fail=0.4，其余为 0
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.2,  # > 0.15
        login_fail_ratio=0.4,    # > 0.3
    ))
    # 基础分: 0.25*0.2 + 0.15*0.4 = 0.05 + 0.06 = 0.11 → 11.0
    # +15 = 26.0
    expected_base = (0.25 * 0.2 + 0.15 * 0.4) * 100.0
    expected = expected_base + 15.0
    assert result["score"] == pytest.approx(expected)


def test_rule_boost_tx_amount():
    """
    规则8：tx_freq > 10 且 amount_anomaly_score > 0.3，额外 +15 分
    tx_freq=15, amount=0.5，其余为 0
    注意 tx_freq 归一化会贡献少量基础分
    """
    result = score_risk(_make_features(
        tx_freq=15.0,             # > 10
        amount_anomaly_score=0.5, # > 0.3
    ))
    # 基础分: 0.20*min(1,15/100) + 0.20*0.5 = 0.03 + 0.10 = 0.13 → 13.0
    # +15 = 28.0
    expected_base = (0.20 * min(1.0, 15.0 / 100.0) + 0.20 * 0.5) * 100.0
    expected = expected_base + 15.0
    assert result["score"] == pytest.approx(expected)


# ── 边界值测试 ────────────────────────────────────────────

def test_score_clamp_upper():
    """测试分数上限钳制到 100"""
    result = score_risk(_make_features(
        device_reuse_ratio=1.0,
        ip_change_freq=1.0,
        tx_freq=200.0,  # 归一化后 1.0
        login_fail_ratio=1.0,
        amount_anomaly_score=1.0,
    ))
    # 全1 + 5个规则都触发 -> 100 + 74 = 174，钳制到 100
    assert result["score"] == pytest.approx(100.0)
    assert result["level"] == "HIGH"


def test_score_clamp_lower():
    """测试负值特征不会导致分数低于 0"""
    # 不该出现负值，但如果出现，应钳制
    result = score_risk(_make_features(
        device_reuse_ratio=-0.5,
        ip_change_freq=-0.5,
        tx_freq=-10.0,
        login_fail_ratio=-0.5,
        amount_anomaly_score=-0.5,
    ))
    assert result["score"] == pytest.approx(0.0)
    assert result["level"] == "LOW"


def test_tx_freq_normalization():
    """
    测试 tx_freq 归一化：min(1.0, tx_freq / 100)
    tx_freq=200 归一化后为 1.0
    """
    result = score_risk(_make_features(
        device_reuse_ratio=0.0,
        ip_change_freq=0.0,
        tx_freq=200.0,  # 归一化 = 1.0
        login_fail_ratio=0.0,
        amount_anomaly_score=0.0,
    ))
    # 基础分: 0.20 * 1.0 * 100 = 20.0
    assert result["score"] == pytest.approx(20.0)


# ── 等级映射测试 ──────────────────────────────────────────

@pytest.mark.parametrize("score_value,expected_level,expected_range", [
    (0.0, "LOW", "0~30"),
    (15.0, "LOW", "0~30"),
    (30.0, "MEDIUM", "31~70"),   # 规则5触发（device_reuse_ratio=0.3>0.2），+19后=49
    (31.0, "HIGH", "71~100"),    # 规则5/6/7/8触发，+64后=95
    (50.0, "HIGH", "71~100"),    # 规则5/6/7/8触发，+64后=100 钳制
    (70.0, "HIGH", "71~100"),    # 规则5/6/7/8触发，+64后=100 钳制
    (71.0, "HIGH", "71~100"),
    (85.0, "HIGH", "71~100"),
    (100.0, "HIGH", "71~100"),
])
def test_level_mapping(score_value, expected_level, expected_range):
    """测试各分数段的风险等级映射"""
    # 构造一个恰好得到指定分数的特征组合（通过反向计算权重和）
    # 使用最简单的特征组合来得到目标分数
    total_weight = 0.25 + 0.20 + 0.20 + 0.15 + 0.20  # = 1.0
    ratio = score_value / 100.0

    features = _make_features(
        device_reuse_ratio=ratio,
        ip_change_freq=ratio,
        tx_freq=ratio * 100.0,  # 这样归一化后 = ratio
        login_fail_ratio=ratio,
        amount_anomaly_score=ratio,
    )
    result = score_risk(features)
    assert result["level"] == expected_level
    assert result["level_range"] == expected_range


# ── 输出结构测试 ──────────────────────────────────────────

def test_output_structure():
    """测试输出 dict 结构"""
    result = score_risk(_make_features())
    assert isinstance(result, dict)
    assert set(result.keys()) == {"score", "level", "level_range"}
    assert isinstance(result["score"], float)
    assert isinstance(result["level"], str)
    assert isinstance(result["level_range"], str)


def test_output_example():
    """
    测试 CLAUDE.md 中的示例：
    device_reuse=0.82, ip_change=0.45, tx_freq=12, login_fail=0.30, amount_anomaly=0.67
    规则5(+19)、规则6(+15)、规则8(+15)触发，总计 +49
    期望得到约 98.8 分，HIGH 等级。
    """
    result = score_risk({
        "device_reuse_ratio": 0.82,
        "ip_change_freq": 0.45,
        "tx_freq": 12.0,
        "login_fail_ratio": 0.30,
        "amount_anomaly_score": 0.67,
    })
    # 基础分 + 规则5(+19) + 规则6(+15) + 规则8(+15) = +49
    expected = (0.25 * 0.82 + 0.20 * 0.45 + 0.20 * (12.0 / 100.0) + 0.15 * 0.30 + 0.20 * 0.67) * 100 + 49.0
    assert result["score"] == pytest.approx(expected)
    assert result["level"] == "HIGH"
    assert result["level_range"] == "71~100"
