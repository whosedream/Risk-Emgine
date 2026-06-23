"""
完整评估脚本 — 训练集/验证集/测试集 全部跑一遍，对比 ground truth

用法: uv run python run_eval.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, classification_report
from scipy.stats import spearmanr
from feature_extraction import extract_features_per_user
from scoring_model import score_risk, score_risk_hybrid

DATA_DIR = "data/splits"
SPLITS = ["train", "val", "test"]
LEVEL_CN = {0: "低风险", 1: "中风险", 2: "高风险"}


def run_split(name):
    path = os.path.join(DATA_DIR, f"{name}.csv")
    df = pd.read_csv(path)
    tmp = os.path.join(DATA_DIR, f"_tmp_{name}.csv")
    df.to_csv(tmp, index=False)

    per_user = extract_features_per_user(tmp)
    labels = df.groupby("user_id")["label"].first()
    os.remove(tmp)

    rows = []
    for uid in per_user:
        r_rule = score_risk(per_user[uid])
        r_ml = score_risk_hybrid(per_user[uid], alpha=0.0)
        rows.append({
            "account_id": uid,
            "true_label": int(labels[uid]),
            "rule_score": r_rule["score"],
            "rule_level": r_rule["level"],
            "ml_score": r_ml["score"],
            "ml_level": r_ml["level"],
        })

    df_r = pd.DataFrame(rows)
    df_r["rule_pred"] = df_r["rule_level"].map({"LOW": 0, "MEDIUM": 1, "HIGH": 2})
    df_r["ml_pred"] = df_r["ml_level"].map({"LOW": 0, "MEDIUM": 1, "HIGH": 2})

    y_true = df_r["true_label"].values
    y_rule = df_r["rule_pred"].values
    y_ml = df_r["ml_pred"].values

    # 指标
    acc_r = accuracy_score(y_true, y_rule)
    acc_m = accuracy_score(y_true, y_ml)
    k_r = cohen_kappa_score(y_true, y_rule)
    k_m = cohen_kappa_score(y_true, y_ml)
    sr_r, _ = spearmanr(y_true, df_r["rule_score"])
    sr_m, _ = spearmanr(y_true, df_r["ml_score"])

    print(f"\n{'='*70}")
    print(f"  {name.upper()}  ({len(df_r)} 账户)")
    print(f"{'='*70}")
    print(f"  {'':>15} {'规则':>10} {'ML(Ensemble)':>15}")
    print(f"  {'准确率':>15} {acc_r:>9.1%} {acc_m:>14.1%}")
    print(f"  {'Kappa':>15} {k_r:>10.3f} {k_m:>14.3f}")
    print(f"  {'Spearman r':>15} {sr_r:>10.3f} {sr_m:>14.3f}")
    print()

    # 逐账户对比
    print(f"  {'账户':<14} {'真实':<8} {'规则':>6} {'ML':>6} {'规则分':>7} {'ML分':>7} 结果")
    print(f"  {'-'*60}")
    ok_r = ok_m = 0
    for _, row in df_r.iterrows():
        r_ok = row["true_label"] == row["rule_pred"]
        m_ok = row["true_label"] == row["ml_pred"]
        ok_r += r_ok
        ok_m += m_ok
        tag = "✅" if r_ok else ("⚠️" if m_ok else "❌")
        print(f"  {row['account_id']:<14} {LEVEL_CN[row['true_label']]:<8} "
              f"{row['rule_pred']:>5} {row['ml_pred']:>5} "
              f"{row['rule_score']:>6.0f} {row['ml_score']:>6.0f}  {tag}")

    print(f"\n  规则命中: {ok_r}/{len(df_r)}   ML命中: {ok_m}/{len(df_r)}")

    return {
        "name": name,
        "accounts": len(df_r),
        "rule_acc": round(acc_r, 4),
        "ml_acc": round(acc_m, 4),
        "rule_kappa": round(k_r, 4),
        "ml_kappa": round(k_m, 4),
        "rule_spearman": round(sr_r, 4),
        "ml_spearman": round(sr_m, 4),
    }


# ── 主流程 ──────────────────────────────────────────
print("风控模型评估 — 规则 vs ML(Ensemble) 对比 ground truth")
results = []
for name in SPLITS:
    if os.path.exists(f"{DATA_DIR}/{name}.csv"):
        results.append(run_split(name))
    else:
        print(f"\n  {name}: 文件不存在，跳过")

# 汇总
print(f"\n{'='*70}")
print("  汇总")
print(f"{'='*70}")
print(f"  {'集合':<8} {'账户':>5} {'规则Acc':>8} {'ML Acc':>8} {'规则Kappa':>10} {'ML Kappa':>10}")
for r in results:
    print(f"  {r['name']:<8} {r['accounts']:>5} {r['rule_acc']:>7.1%} {r['ml_acc']:>7.1%} "
          f"{r['rule_kappa']:>10.3f} {r['ml_kappa']:>10.3f}")
