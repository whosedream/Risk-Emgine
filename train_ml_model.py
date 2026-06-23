"""
ML 模型训练 — 对比规则打分 vs 机器学习在测试集上的效果
训练集 69 账户，验证集 16 账户，测试集 15 账户
"""
import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import cross_val_score
from scipy.stats import spearmanr
import xgboost as xgb

from feature_extraction import extract_features_per_user
from scoring_model import score_risk

FEATURE_NAMES = [
    "device_reuse_ratio", "ip_change_freq", "tx_freq",
    "login_fail_ratio", "amount_anomaly_score",
    "behavior_time_anomaly", "multi_region_risk",
    "tx_velocity_5min", "tx_velocity_1h",
    "device_switch_24h", "ip_switch_24h",
    "tx_interval_mean_sec", "tx_burst_ratio",
    "amount_user_deviation", "amount_user_max_ratio",
    "night_tx_ratio", "odd_hour_tx_ratio",
]

# ── 1. 提取所有集合的 per-user 特征 ─────────────────
def get_features_and_labels(split_name):
    """从 split CSV 提取 per-user 特征向量 + label"""
    path = f"data/splits/{split_name}.csv"
    df = pd.read_csv(path)
    tmp = f"data/splits/_tmp_{split_name}.csv"
    df.to_csv(tmp, index=False)

    per_user = extract_features_per_user(tmp)
    labels = df.groupby("user_id")["label"].first()

    X, y, uids = [], [], []
    for uid in per_user:
        feat = [per_user[uid][k] for k in FEATURE_NAMES]
        X.append(feat)
        y.append(int(labels[uid]))
        uids.append(uid)

    os.remove(tmp)
    return np.array(X), np.array(y), uids

print("加载特征...")
X_train, y_train, _ = get_features_and_labels("train")
X_val,   y_val,   _ = get_features_and_labels("val")
X_test,  y_test,  test_uids = get_features_and_labels("test")

print(f"训练集: {X_train.shape}, 验证集: {X_val.shape}, 测试集: {X_test.shape}")
print(f"训练集 label 分布: {np.bincount(y_train)}")

# ── 2. 标准化 ──────────────────────────────────────
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled   = scaler.transform(X_val)
X_test_scaled  = scaler.transform(X_test)

# ── 3. 规则模型 baseline ───────────────────────────
def rule_predictions(X, uids, df_path="data/splits/test.csv"):
    """用规则模型打分并返回预测"""
    df = pd.read_csv(df_path)
    tmp = "data/splits/_tmp_rule.csv"
    df.to_csv(tmp, index=False)
    per_user = extract_features_per_user(tmp)
    preds, scores = [], []
    for uid in uids:
        r = score_risk(per_user[uid])
        preds.append({"LOW": 0, "MEDIUM": 1, "HIGH": 2}[r["level"]])
        scores.append(r["score"])
    os.remove(tmp)
    return np.array(preds), np.array(scores)

print("\n=== 规则模型 (baseline) ===")
rule_preds, rule_scores = rule_predictions(X_test, test_uids)
print(classification_report(y_test, rule_preds, target_names=["LOW", "MEDIUM", "HIGH"], zero_division=0))
print(f"Accuracy: {accuracy_score(y_test, rule_preds):.2%}")
r_rule, _ = spearmanr(y_test, rule_scores)
print(f"Spearman r: {r_rule:.3f}")

# ── 4. ML 模型 ─────────────────────────────────────
models = {
    "RandomForest":       RandomForestClassifier(n_estimators=100, max_depth=3, min_samples_leaf=3, class_weight="balanced", random_state=42),
    "GradientBoosting":   GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42),
    "XGBoost":            xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05,
                                             subsample=0.8, colsample_bytree=0.8,
                                             eval_metric="mlogloss", random_state=42),
}

for name, model in models.items():
    print(f"\n=== {name} ===")

    # 训练
    model.fit(X_train_scaled, y_train)

    # 交叉验证
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
    print(f"5-fold CV accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")

    # 验证集
    val_preds = model.predict(X_val_scaled)
    val_acc = accuracy_score(y_val, val_preds)
    print(f"验证集 accuracy: {val_acc:.2%}")

    # 测试集
    test_preds = model.predict(X_test_scaled)
    test_proba = model.predict_proba(X_test_scaled)

    # 用概率期望值作为连续评分 (0 * P(LOW) + 1 * P(MEDIUM) + 2 * P(HIGH))
    ml_scores = test_proba @ np.array([0, 1, 2])

    print(classification_report(y_test, test_preds, target_names=["LOW", "MEDIUM", "HIGH"], zero_division=0))
    acc = accuracy_score(y_test, test_preds)
    r_ml, p_ml = spearmanr(y_test, ml_scores)
    print(f"Accuracy: {acc:.2%}  Spearman r: {r_ml:.3f} (p={p_ml:.4f})")

    # 显示测试集预测详情
    print(f"\n{'账户':<12} {'真实':>4} {'规则':>4} {'ML':>4} {'规则分':>6} {'ML分':>6}")
    for i, uid in enumerate(test_uids):
        print(f"{uid:<12} {y_test[i]:>4} {rule_preds[i]:>4} {test_preds[i]:>4} "
              f"{rule_scores[i]:>6.1f} {ml_scores[i]:>6.2f}")

# ── 5. Ensemble: RF + XGBoost + GBDT 软投票 ────────
print("\n=== Voting Ensemble (RF + XGBoost + GBDT) ===")
ensemble = VotingClassifier(
    estimators=[
        ("rf", models["RandomForest"]),
        ("xgb", models["XGBoost"]),
        ("gbdt", models["GradientBoosting"]),
    ],
    voting="soft",
)
ensemble.fit(X_train_scaled, y_train)
cv_e = cross_val_score(ensemble, X_train_scaled, y_train, cv=5)
print(f"5-fold CV accuracy: {cv_e.mean():.2%} (+/- {cv_e.std():.2%})")
val_preds = ensemble.predict(X_val_scaled)
val_acc = accuracy_score(y_val, val_preds)
print(f"验证集 accuracy: {val_acc:.2%}")
test_preds = ensemble.predict(X_test_scaled)
test_proba = ensemble.predict_proba(X_test_scaled)
ens_scores = test_proba @ np.array([0, 1, 2])
print(classification_report(y_test, test_preds, target_names=["LOW", "MEDIUM", "HIGH"], zero_division=0))
acc = accuracy_score(y_test, test_preds)
r_ens, p_ens = spearmanr(y_test, ens_scores)
print(f"Accuracy: {acc:.2%}  Spearman r: {r_ens:.3f} (p={p_ens:.4f})")

# ── 6. Isolation Forest 无监督基线 ─────────────────
print("\n=== Isolation Forest (无监督基线) ===")
from sklearn.ensemble import IsolationForest
iso = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
iso_scores = -iso.fit_predict(X_train_scaled)  # -1=异常→+1
# 将异常分数归一化到 0-100
iso_norm = (iso.decision_function(X_test_scaled) * -1)  # 越低越异常
iso_norm = (iso_norm - iso_norm.min()) / (iso_norm.max() - iso_norm.min() + 1e-8) * 100
iso_preds = np.where(iso_norm > 55, 2, np.where(iso_norm > 30, 1, 0))
r_iso, p_iso = spearmanr(y_test, iso_norm)
print(f"Spearman r: {r_iso:.3f} (p={p_iso:.4f})")
print(classification_report(y_test, iso_preds, target_names=["LOW", "MEDIUM", "HIGH"], zero_division=0))

# ── 7. 特征重要性 ──────────────────────────────────
print("\n=== 特征重要性 ===")
rf = models["RandomForest"]
xgb_model = models["XGBoost"]
for name, rf_imp, xgb_imp in sorted(
    zip(FEATURE_NAMES, rf.feature_importances_, xgb_model.feature_importances_),
    key=lambda x: -x[1]
):
    bar = "█" * int(rf_imp * 50)
    print(f"  {name:<25} RF={rf_imp:.3f} XGB={xgb_imp:.3f} {bar}")

# ── 8. 保存模型 ────────────────────────────────────
import joblib
os.makedirs("data/model", exist_ok=True)
joblib.dump(scaler, "data/model/scaler.pkl")
joblib.dump(rf, "data/model/random_forest.pkl")
joblib.dump(xgb_model, "data/model/xgboost.pkl")
joblib.dump(ensemble, "data/model/ensemble.pkl")
print("\n模型已保存: data/model/{scaler,random_forest,xgboost,ensemble}.pkl")
print(f"\n最佳单模型: {'XGBoost' if max(models['XGBoost'].feature_importances_) > 0 else 'RandomForest'}")
