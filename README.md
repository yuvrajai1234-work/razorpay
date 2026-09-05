# 🛡️ RazorPay FraudGuard & Dispute Engine

> **Track 02: Next-Gen Risk Mitigation & Automated Dispute Resolution**  
> An enterprise-grade, defense-only fraud detection pipeline, real-time scoring microservice, automated Visa/Mastercard dispute representment engine, and interactive operations dashboard.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![XGBoost](https://img.shields.io/badge/XGBoost-EB8E24?style=for-the-badge&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![SHAP](https://img.shields.io/badge/SHAP-Explainable_AI-blue?style=for-the-badge)](https://shap.readthedocs.io)
[![ReportLab](https://img.shields.io/badge/ReportLab-PDF_Engine-darkgreen?style=for-the-badge)](https://www.reportlab.com)
[![Pytest](https://img.shields.io/badge/Pytest-Passing-brightgreen?style=for-the-badge&logo=pytest)](https://pytest.org)

---

## 📌 1. Problem Statement: The $100B+ Chargeback & Friendly Fraud Crisis

Digital merchants face a compounding dual threat in card-not-present (CNP) e-commerce:

1. **First-Party Fraud / Return Abuse (Friendly Fraud)**: Legitimate customers exploit card scheme protections by falsely claiming non-receipt or unrecognized charges after receiving goods.
2. **First-Line False Positive Friction**: Overly aggressive blocking rules alienate trustworthy customers ($15 per rejected checkout in lost lifetime value and friction), while lax rules result in direct chargeback fees ($50 per dispute) and payment network penalty monitoring programs.
3. **Representment Overhead**: Card networks (Visa/Mastercard) provide strict representment rebuttal windows (usually 30 days). Small merchants lose up to 80% of winnable disputes because gathering EMV 3DS logs, carrier tracking, AVS/CVV audits, and drafting compliant rebuttal packets is manual and time-consuming.

---

## 🏆 2. Held-Out Test Set Results

The ML detection pipeline was trained on **284,807 transactions** (0.1727% extreme class imbalance) using a strict **80/20 stratified train-test split**. The 56,962-transaction test set was held out and locked.

To avoid distribution shift on extreme imbalance, decision threshold calibration was conducted using **5-Fold Out-of-Fold (OOF) Cross-Validation** on the training set, maximizing recall subject to a hard $\ge 88\%$ precision target.

### Performance Scorecard (Held-Out Test Set: 56,962 Transactions)

| Metric | Target | Held-Out Score | Status | Business Meaning |
|---|---|:---:|:---:|---|
| **Precision** | $\ge 88.0\%$ | **89.01%** | **Target Met ✅** | When model flags fraud, it is correct 89% of the time (low customer friction). |
| **Recall** | $\ge 78.0\%$ | **82.65%** | **Target Met ✅** | Model successfully intercepts 82.7% of all fraud attacks. |
| **ROC-AUC** | — | **0.9773** | High Discriminative Power | Near-perfect separation across the entire risk spectrum. |
| **PR-AUC (Avg Precision)** | — | **0.8811** | Imbalance Robust | High precision maintained across broad recall tiers. |
| **Decision Threshold** | Calibrated | **0.6723** | OOF Calibrated | Statistically calibrated threshold (via 5-fold CV). |

#### Confusion Matrix (98 True Frauds, 56,864 Legitimate Orders)

```
                       Actual Legit (0)    Actual Fraud (1)
Predicted Legit (0)         56,854 (TN)             17 (FN)
Predicted Fraud (1)             10 (FP)             81 (TP)
```

---

## 💰 3. Honest Metrics: Cost-Sensitive Net Value Economics

Traditional ML accuracy metrics (e.g., 99.9% accuracy) are misleading in fraud detection. FraudGuard uses an **Honest Cost-Sensitive Financial Objective Function** balancing chargeback fee recovery against false-positive customer friction:

### Cost Objective Function

$$\text{Net Merchant Value Saved} = (\text{TP} \times \$50) - (\text{FP} \times \$15) - (\text{FN} \times \$50)$$

Where:
- **True Positive ($\text{TP} \times +\$50$)**: Fraud successfully prevented $\rightarrow$ chargeback penalty and product loss recovered.
- **False Positive ($\text{FP} \times -\$15$)**: Legitimate cardholder blocked $\rightarrow$ customer service overhead and friction penalty.
- **False Negative ($\text{FN} \times -\$50$)**: Fraud slipped through $\rightarrow$ merchant absorbs chargeback fee and inventory loss.

### Financial Yield (Held-Out Test Set: 56,962 Transactions)

| Component | Quantity | Unit Impact | Financial Total |
|---|:---:|:---:|:---:|
| **Gross Chargeback Recovery** | $81\text{ TPs}$ | $+\$50.00$ | **$+\$4,050.00$** |
| **False Positive Friction Cost** | $10\text{ FPs}$ | $-\$15.00$ | **$-\$150.00$** |
| **Missed Fraud Loss** | $17\text{ FNs}$ | $-\$50.00$ | **$-\$850.00$** |
| **Net Realized Merchant Savings** | — | — | **$\$3,050.00$** |
| **ROI vs. Oracle Maximum Baseline** | — | — | **$62.2\%$** |

---

## 🛡️ 4. Architectural Guardrails & Defense-Only Mechanics

```
                   ┌────────────────────────────────────────────────────────┐
                   │               MERCHANT CHECKOUT PAYLOAD                │
                   └──────────────────────────┬─────────────────────────────┘
                                              │
                                  [ FEATURE STANDARDIZATION ]
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        │                                           │
             [ AI / PROBABILISTIC LAYER ]               [ NON-AI / DETERMINISTIC RULES ]
                        │                                           │
         • XGBoost (`scale_pos_weight` = 577.3)      • Hard Velocity Filters & Blocklists
         • SHAP TreeExplainer Attribution            • 4-Tier Governance Policy Router
         • Real-time Feature Contribution            • Visa/Mastercard Rebuttal Compiler
                        │                                           │
                        └─────────────────────┬─────────────────────┘
                                              │
                   ┌──────────────────────────▼─────────────────────────────┐
                   │             ACTIONABLE GOVERNANCE DECISION             │
                   │   • Critical (≥85%): DECLINE_AND_BLOCK                 │
                   │   • High (≥67.2%): MANUAL_REVIEW_OR_3DS                │
                   │   • Medium (≥30%): CHALLENGE_3DS                       │
                   │   • Low (<30%): APPROVE_INSTANT                        │
                   └────────────────────────────────────────────────────────┘
```

### 1. Strict Defense-Only Mechanics
- **No Autonomous Money Movement**: The system cannot debit accounts, alter fees, or issue arbitrary refunds without verified merchant authorization.
- **Fail-Safe Fallbacks**: If the ML engine fails to initialize or experiences latency timeouts, traffic automatically falls back to standard 3-D Secure step-up authentication.

### 2. SHAP Explainability & White-Box Auditing
- Every scoring response includes **Local SHAP TreeExplainer attributions**, revealing the top 3 driving features and exact directional impacts (`increase_risk` / `decrease_risk`).
- Eliminates "black-box" rejections and provides human risk officers with transparent justification.

### 3. Explicit AI vs. Non-AI Logic Boundaries
- **AI Scope**: Probabilistic risk estimation, pattern anomaly detection, and continuous feature attribution.
- **Deterministic Non-AI Scope**: Scheme compliance rules (Visa Rule 10.4 / Mastercard Rule 4837), SLA queue timeouts, and automated ReportLab PDF representment document compilation.

---

## 🏗️ 5. Project Architecture

```
RazorPay/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI microservice with CORS & OpenAPI schema support
│   ├── schemas.py           # Pydantic v2 schemas for scoring & dispute evidence
│   └── pdf_generator.py     # ReportLab Visa/Mastercard representment rebuttal engine
├── frontend/
│   └── app.py               # 3-Tab Streamlit Dashboard (Simulator, Queue, Governance)
├── tests/
│   ├── __init__.py
│   └── test_api.py          # Pytest suite testing all endpoints and schemas
├── fraud_pipeline.py        # Core ML training, OOF calibration & SHAP export script
├── model.joblib             # Serialized XGBoost model artifact (1.05 MB)
├── scaler.joblib            # StandardScaler for Time and Amount
├── metrics.json             # Model evaluation payload, metrics & SHAP rankings
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Pinned production dependencies
└── .gitignore               # Excludes raw CSV data (>100MB) from git tracking
```

---

## 🚀 6. Quickstart Guide

### Prerequisites
- Python 3.9+ (Windows, macOS, or Linux)
- Git

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yuvrajai1234-work/razorpay.git
cd razorpay

# 2. Install dependencies
pip install -r requirements.txt
```

### Running the Complete Stack

Open two terminal windows:

#### Terminal 1: FastAPI Backend
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Terminal 2: Streamlit Frontend
```bash
python -m streamlit run frontend/app.py --server.port 8501
```
- **Dashboard UI**: [http://localhost:8501](http://localhost:8501)

---

## 📡 7. API Reference

### 1. `POST /score-order`
Evaluates real-time transaction features against the trained XGBoost model.

#### Request Body
```json
{
  "order_id": "ORD-2026-9481",
  "time": 406.0,
  "amount": 259.99,
  "v1": -2.3122,
  "v4": 3.9979,
  "v10": -2.7141,
  "v12": -3.1023,
  "v14": -4.8405
}
```

#### Response (`200 OK`)
```json
{
  "order_id": "ORD-2026-9481",
  "fraud_probability": 0.941208,
  "risk_tier": "Critical",
  "decision_action": "DECLINE_AND_BLOCK",
  "decision_threshold": 0.67231,
  "is_fraud_flagged": true,
  "top3_risk_drivers": [
    { "feature": "V14", "shap_value": 3.489102, "direction": "increase_risk", "feature_value": -4.8405 },
    { "feature": "V4", "shap_value": 2.189401, "direction": "increase_risk", "feature_value": 3.9979 },
    { "feature": "V12", "shap_value": 1.452091, "direction": "increase_risk", "feature_value": -3.1023 }
  ],
  "model_version": "XGBClassifier-v1.0-ScalePosWeight"
}
```

### 2. `POST /generate-evidence`
Generates a formal Visa/Mastercard chargeback representment rebuttal PDF packet.

- **Accepts**: Order reference, AVS/CVV status, 3DS liability shift logs, carrier tracking, and authorization audit trail.
- **Returns**: Binary PDF stream (`Content-Type: application/pdf`) with formal case summary, security certifications, delivery proof, and legal representment statement.

---

## 🖥️ 8. Streamlit Dashboard Features

The dashboard at `http://localhost:8501` provides three dedicated operational tabs:

1. **⚡ Tab 1 (Checkout Simulator)**:
   - Interactive transaction feature sliders with presets for *Legitimate Order*, *High-Risk Fraud*, and *Borderline 3DS*.
   - Dynamic Plotly **Risk Gauge** and **Top 3 SHAP Attribution Waterfall** chart.
2. **📑 Tab 2 (Dispute Queue & Auto-Responder)**:
   - Queue of active mock disputes with one-click **"Generate Visa/Mastercard Rebuttal PDF"**.
   - Built-in **inline PDF document preview** (`<iframe>` viewer) and instant download.
3. **📊 Tab 3 (Governance & Audit Log)**:
   - 4-Tier Risk Classification Policy table.
   - Live Model Performance Scorecard and Cost-Sensitive Net Savings visualizer.
   - Global Top-10 SHAP feature importance rankings.

---

## 🧪 9. Automated Testing

Run the full pytest suite to verify all API endpoints and schemas:

```bash
python -m pytest -v
```

```
============================= test session starts =============================
platform win32 -- Python 3.9.0, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\yuvra\Coding Projects\RazorPay
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.12.1
collected 4 items

tests/test_api.py::test_health_endpoint PASSED                           [ 25%]
tests/test_api.py::test_score_order_low_risk PASSED                      [ 50%]
tests/test_api.py::test_score_order_high_risk PASSED                     [ 75%]
tests/test_api.py::test_generate_evidence_pdf_success PASSED             [100%]

============================== 4 passed in 3.38s ==============================
```

---
#10 Deployments

Frontend:https://razorpay-frontend-119x.onrender.com/
Backend:https://razorpay-backend-wvbl.onrender.com
