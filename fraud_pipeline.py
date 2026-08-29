# -*- coding: utf-8 -*-
"""
Fraud Detection ML Pipeline
============================
Credit Card Fraud Detection using XGBoost with:
  - StandardScaler on Time & Amount
  - Stratified 80/20 train-test split (test set never touched during calibration)
  - scale_pos_weight to handle extreme class imbalance (0.17%)
  - Out-of-Fold (OOF) 5-fold CV for robust threshold calibration
    (pools ~394 fraud predictions vs. 49 in a naive single-val approach)
  - Threshold strategy: maximize recall subject to precision >= 88%
  - Cost-Sensitive Net Savings: $50/TP chargeback recovery - $15/FP friction
  - SHAP TreeExplainer: global Top-10 + Top-3 per-prediction risk drivers
  - Artifacts: model.joblib + metrics.json
"""

import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────
# 1. Load Dataset
# ─────────────────────────────────────────────────────────
print("=" * 60)
print("  CREDIT CARD FRAUD DETECTION PIPELINE")
print("=" * 60)
print("\n[1/8] Loading dataset...")

df = pd.read_csv("creditcard.csv")
print(f"      Rows: {len(df):,}  |  Columns: {df.shape[1]}")
fraud_pct = df["Class"].mean() * 100
print(f"      Fraud rate: {fraud_pct:.4f}%  ({df['Class'].sum()} fraudulent / {len(df):,} total)")

# ─────────────────────────────────────────────────────────
# 2. Feature Scaling (Time + Amount)
# ─────────────────────────────────────────────────────────
print("\n[2/8] Scaling Time & Amount with StandardScaler...")

scaler = StandardScaler()
df["scaled_time"]   = scaler.fit_transform(df[["Time"]])
df["scaled_amount"] = scaler.fit_transform(df[["Amount"]])

feature_cols = (
    [c for c in df.columns if c.startswith("V")]   # PCA components V1-V28
    + ["scaled_time", "scaled_amount"]
)
X = df[feature_cols].values
y = df["Class"].values
print(f"      Feature matrix shape: {X.shape}  |  Features: {len(feature_cols)}")

# ─────────────────────────────────────────────────────────
# 3. Stratified 80/20 Train-Test Split
# ─────────────────────────────────────────────────────────
print("\n[3/8] Stratified 80/20 train-test split...")

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.20,
    random_state=42,
    stratify=y,
)
print(f"      Train: {X_train.shape[0]:,}  |  Test: {X_test.shape[0]:,}")
print(f"      Train fraud: {y_train.sum()}  |  Test fraud: {y_test.sum()}")
print(f"      NOTE: Test set is locked — never used for threshold calibration.")

# ─────────────────────────────────────────────────────────
# 4. XGBoost Hyperparameters
# ─────────────────────────────────────────────────────────
neg_count = int((y_train == 0).sum())
pos_count = int((y_train == 1).sum())
spw = neg_count / pos_count

xgb_params = dict(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=spw,
    eval_metric="aucpr",
    use_label_encoder=False,
    random_state=42,
    n_jobs=-1,
    tree_method="hist",
)
print(f"\n[4/8] XGBClassifier configured.")
print(f"      scale_pos_weight = {spw:.2f}  ({neg_count:,} neg / {pos_count} pos)")

# ─────────────────────────────────────────────────────────
# 5. Out-of-Fold (OOF) Threshold Calibration
#    5-fold stratified CV on X_train pools ~394 OOF fraud
#    predictions for a statistically robust threshold search.
# ─────────────────────────────────────────────────────────
print("\n[5/8] Out-of-Fold (OOF) threshold calibration (5-fold CV)...")

PREC_TARGET        = 0.88   # hard target on test set
REC_TARGET         = 0.78   # hard target on test set
N_FOLDS            = 5
# OOF models train on (N-1)/N of X_train; the final model trains on 100%.
# A ~3% calibration margin on OOF precision compensates for this gap.
CALIBRATION_MARGIN = 0.03
PREC_TARGET_OOF    = PREC_TARGET + CALIBRATION_MARGIN  # 91% on OOF -> ~88% on test

skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
oof_probs = np.zeros(len(y_train))

t0 = time.time()
for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
    Xf_tr, Xf_val = X_train[tr_idx], X_train[val_idx]
    yf_tr, yf_val = y_train[tr_idx], y_train[val_idx]

    fold_spw = (yf_tr == 0).sum() / max((yf_tr == 1).sum(), 1)
    fold_params = {**xgb_params, "scale_pos_weight": fold_spw}

    m = XGBClassifier(**fold_params)
    m.fit(Xf_tr, yf_tr, verbose=False)
    oof_probs[val_idx] = m.predict_proba(Xf_val)[:, 1]

    print(f"      Fold {fold}/{N_FOLDS}  fraud in fold-val: {yf_val.sum()}")

oof_elapsed = time.time() - t0
total_oof_fraud = y_train.sum()
print(f"\n      OOF calibration done in {oof_elapsed:.1f}s")
print(f"      Total OOF fraud predictions available: {total_oof_fraud}")

# Find threshold on pooled OOF: maximize recall s.t. precision >= PREC_TARGET_OOF
precisions_oof, recalls_oof, thresholds_oof = precision_recall_curve(y_train, oof_probs)
prec_arr = precisions_oof[:-1]
rec_arr  = recalls_oof[:-1]

prec_feasible = prec_arr >= PREC_TARGET_OOF
if prec_feasible.any():
    # Among OOF-feasible thresholds, maximise recall
    feasible_idx    = np.where(prec_feasible)[0]
    best_thresh_idx = feasible_idx[np.argmax(rec_arr[feasible_idx])]
    best_threshold  = float(thresholds_oof[best_thresh_idx])
    strategy        = (f"max-recall s.t. OOF-precision>={PREC_TARGET_OOF:.0%} "
                       f"(+{CALIBRATION_MARGIN:.0%} margin for OOF->final gap)")
else:
    # Fallback: F2 (recall-biased) if adjusted target is unachievable on OOF
    print(f"      WARNING: OOF precision>={PREC_TARGET_OOF:.0%} unachievable -- using F2 fallback.")
    fbeta2 = (1 + 4) * (prec_arr * rec_arr) / ((4 * prec_arr) + rec_arr + 1e-9)
    best_thresh_idx = int(np.argmax(fbeta2))
    best_threshold  = float(thresholds_oof[best_thresh_idx])
    strategy        = "F2-maximising (fallback)"

print(f"      Strategy: {strategy}")
print(f"      Chosen threshold: {best_threshold:.4f}")
print(f"      OOF diagnostics at threshold:")
print(f"        Precision={prec_arr[best_thresh_idx]:.4f}  Recall={rec_arr[best_thresh_idx]:.4f}")

# ─────────────────────────────────────────────────────────
# 6. Final Model — Retrain on Full X_train
# ─────────────────────────────────────────────────────────
print(f"\n[6/8] Training final XGBClassifier on full training set...")

model = XGBClassifier(**xgb_params)
t0 = time.time()
model.fit(X_train, y_train, verbose=False)
elapsed = time.time() - t0
print(f"      Training complete in {elapsed:.1f}s")

# Evaluate on sacred test set
y_prob = model.predict_proba(X_test)[:, 1]
y_pred = (y_prob >= best_threshold).astype(int)

precision = precision_score(y_test, y_pred, zero_division=0)
recall    = recall_score(y_test, y_pred, zero_division=0)
roc_auc   = roc_auc_score(y_test, y_prob)
avg_prec  = average_precision_score(y_test, y_prob)
cm        = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()

print(f"\n      {'Metric':<30} {'Value':>10}")
print(f"      {'-'*42}")
print(f"      {'Precision':<30} {precision:>10.4f}  {'[OK >= 88%]' if precision >= 0.88 else '[MISS < 88%]'}")
print(f"      {'Recall':<30} {recall:>10.4f}  {'[OK >= 78%]' if recall >= 0.78 else '[MISS < 78%]'}")
print(f"      {'ROC-AUC':<30} {roc_auc:>10.4f}")
print(f"      {'Avg Precision (PR-AUC)':<30} {avg_prec:>10.4f}")
print(f"      {'True Positives  (TP)':<30} {tp:>10}")
print(f"      {'False Positives (FP)':<30} {fp:>10}")
print(f"      {'True Negatives  (TN)':<30} {tn:>10}")
print(f"      {'False Negatives (FN)':<30} {fn:>10}")

print("\n      Classification Report:")
print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"], digits=4))

# ─────────────────────────────────────────────────────────
# 7. Cost-Sensitive Net Savings
# ─────────────────────────────────────────────────────────
print("\n[7/8] Computing Cost-Sensitive Net Savings...")

CHARGEBACK_RECOVERY = 50.0   # USD saved per TP (caught fraud, chargeback fee recovered)
FP_FRICTION_COST    = 15.0   # USD lost per FP (legitimate order blocked)


def net_savings(tp: int, fp: int, fn: int) -> dict:
    """
    Cost-Sensitive Net Savings model for fraud detection.

    Decision economics per transaction:
      TP: Fraud caught      -> +$50 chargeback fee recovered
      FP: Legit flagged     -> -$15 customer friction / cancelled order
      FN: Fraud missed      -> -$50 opportunity cost (chargeback not recovered)

    ROI is measured against the theoretical maximum of catching ALL fraud
    (i.e., a perfect-recall, zero-FP oracle baseline).
    """
    gross_savings       = tp * CHARGEBACK_RECOVERY
    false_positive_cost = fp * FP_FRICTION_COST
    missed_fraud_cost   = fn * CHARGEBACK_RECOVERY
    net                 = gross_savings - false_positive_cost - missed_fraud_cost
    baseline            = (tp + fn) * CHARGEBACK_RECOVERY   # oracle: catch all fraud
    roi_pct             = (net / baseline * 100) if baseline > 0 else 0.0
    return {
        "true_positives":             tp,
        "false_positives":            fp,
        "false_negatives":            fn,
        "gross_savings_usd":          gross_savings,
        "false_positive_cost_usd":    false_positive_cost,
        "missed_fraud_cost_usd":      missed_fraud_cost,
        "net_savings_usd":            net,
        "roi_pct":                    roi_pct,
        "chargeback_recovery_per_tp": CHARGEBACK_RECOVERY,
        "friction_cost_per_fp":       FP_FRICTION_COST,
    }


cost_metrics = net_savings(tp, fp, fn)
print(f"      Gross Savings  (TP x ${CHARGEBACK_RECOVERY:.0f}): ${cost_metrics['gross_savings_usd']:>8.2f}")
print(f"      FP Friction    (FP x ${FP_FRICTION_COST:.0f}): ${cost_metrics['false_positive_cost_usd']:>8.2f}  (-)")
print(f"      Missed Fraud   (FN x ${CHARGEBACK_RECOVERY:.0f}): ${cost_metrics['missed_fraud_cost_usd']:>8.2f}  (-)")
print(f"      {'-'*44}")
print(f"      Net Savings:               ${cost_metrics['net_savings_usd']:>8.2f}")
print(f"      ROI vs. oracle baseline:   {cost_metrics['roi_pct']:>7.1f}%")

# ─────────────────────────────────────────────────────────
# 8. SHAP Feature Importance — Top-3 Risk Drivers
# ─────────────────────────────────────────────────────────
print("\n[8/8] Computing SHAP values (TreeExplainer)...")

explainer = shap.TreeExplainer(model)

sample_size = min(2000, len(X_test))
rng         = np.random.default_rng(42)
sample_idx  = rng.choice(len(X_test), size=sample_size, replace=False)
X_sample    = X_test[sample_idx]

shap_values = explainer.shap_values(X_sample)   # (n_samples, n_features)
mean_shap   = np.abs(shap_values).mean(axis=0)

global_importance = sorted(
    zip(feature_cols, mean_shap.tolist()),
    key=lambda kv: kv[1],
    reverse=True,
)

print("\n      Global Top-10 SHAP Feature Importances:")
print(f"      {'Rank':<5} {'Feature':<20} {'Mean |SHAP|':>12}")
print(f"      {'-'*40}")
for rank, (feat, imp) in enumerate(global_importance[:10], 1):
    print(f"      {rank:<5} {feat:<20} {imp:>12.6f}")

# Per-prediction top-3 risk drivers for flagged transactions
sample_probs     = model.predict_proba(X_sample)[:, 1]
fraud_pred_mask  = sample_probs >= best_threshold
fraud_indices    = np.where(fraud_pred_mask)[0]

per_prediction_drivers = []
for i in fraud_indices[:20]:
    shap_row = shap_values[i]
    top3_idx = np.argsort(np.abs(shap_row))[::-1][:3]
    drivers  = [
        {
            "feature":    feature_cols[j],
            "shap_value": float(shap_row[j]),
            "direction":  "increase_risk" if shap_row[j] > 0 else "decrease_risk",
        }
        for j in top3_idx
    ]
    per_prediction_drivers.append({
        "sample_index":      int(i),
        "fraud_probability": float(y_prob[sample_idx[i]]),
        "top3_risk_drivers": drivers,
    })

print(f"\n      Top-3 drivers exported for {len(per_prediction_drivers)} flagged transactions.")
if per_prediction_drivers:
    ex = per_prediction_drivers[0]
    print(f"      Example (sample_idx={ex['sample_index']}, p={ex['fraud_probability']:.4f}):")
    for d in ex["top3_risk_drivers"]:
        print(f"        {d['feature']:<20}  SHAP={d['shap_value']:+.4f}  [{d['direction']}]")

# ─────────────────────────────────────────────────────────
# Save Artifacts
# ─────────────────────────────────────────────────────────
print("\n[Saving artifacts...]")

joblib.dump(model, "model.joblib")
print("      model.joblib saved")

metrics_payload = {
    "model":           "XGBClassifier",
    "dataset":         "creditcard.csv",
    "n_train":         int(X_train.shape[0]),
    "n_test":          int(X_test.shape[0]),
    "n_features":      len(feature_cols),
    "fraud_rate_pct":  round(fraud_pct, 6),
    "threshold_calibration": {
        "method":         "OOF 5-fold stratified CV",
        "strategy":       strategy,
        "decision_threshold": round(best_threshold, 6),
        "oof_precision_at_threshold": round(float(prec_arr[best_thresh_idx]), 6),
        "oof_recall_at_threshold":    round(float(rec_arr[best_thresh_idx]), 6),
    },
    "performance": {
        "precision":       round(precision, 6),
        "recall":          round(recall, 6),
        "roc_auc":         round(roc_auc, 6),
        "pr_auc":          round(avg_prec, 6),
        "true_positives":  int(tp),
        "false_positives": int(fp),
        "true_negatives":  int(tn),
        "false_negatives": int(fn),
        "targets_met": {
            "precision_gte_88pct": bool(precision >= 0.88),
            "recall_gte_78pct":    bool(recall >= 0.78),
        },
    },
    "cost_sensitive_evaluation": cost_metrics,
    "shap_global_top10": [
        {"rank": i + 1, "feature": f, "mean_abs_shap": round(v, 8)}
        for i, (f, v) in enumerate(global_importance[:10])
    ],
    "per_prediction_top3_drivers": per_prediction_drivers,
    "model_hyperparameters": model.get_params(),
}

with open("metrics.json", "w") as f:
    json.dump(metrics_payload, f, indent=2, default=str)
print("      metrics.json saved")

# ─────────────────────────────────────────────────────────
# Final Summary
# ─────────────────────────────────────────────────────────
targets_met = precision >= 0.88 and recall >= 0.78

print("\n" + "=" * 60)
print("  PIPELINE COMPLETE")
print("=" * 60)
print(f"  Threshold (OOF-calibrated): {best_threshold:.4f}")
print(f"  Precision : {precision:.4f}  {'[OK >= 88%]' if precision >= 0.88 else '[MISS < 88%]'}")
print(f"  Recall    : {recall:.4f}  {'[OK >= 78%]' if recall >= 0.78 else '[MISS < 78%]'}")
print(f"  ROC-AUC   : {roc_auc:.4f}")
print(f"  PR-AUC    : {avg_prec:.4f}")
print(f"  Net Savings: ${cost_metrics['net_savings_usd']:.2f}  (ROI {cost_metrics['roi_pct']:.1f}%)")
print(f"\n  Both targets met: {'YES' if targets_met else 'NO'}")
print(f"\n  Artifacts saved:")
print(f"    model.joblib")
print(f"    metrics.json")
print("=" * 60)
