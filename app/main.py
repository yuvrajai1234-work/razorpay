import json
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

import joblib
import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

# Python 3.9 Pydantic JSON Schema compatibility patch for nested Literals
try:
    import pydantic.json_schema as _pydantic_js
    from typing_inspection.introspection import get_literal_values as _get_literal_vals

    def _safe_build_schema_type_to_method(self):
        mapping = {}
        def _extract_strings(tp):
            if isinstance(tp, str):
                yield tp
            else:
                for sub in _get_literal_vals(tp):
                    yield from _extract_strings(sub)

        for key in _extract_strings(_pydantic_js.CoreSchemaOrFieldType):
            method_name = f"{key.replace('-', '_')}_schema"
            if hasattr(self, method_name):
                mapping[key] = getattr(self, method_name)
        return mapping

    _pydantic_js.GenerateJsonSchema.build_schema_type_to_method = _safe_build_schema_type_to_method
except Exception:
    pass

from app.pdf_generator import generate_dispute_pdf
from app.schemas import DisputeEvidenceRequest, ScoreResponse, SHAPDriver, TransactionRequest

# Global model and explainer cache
_ml_resources: Dict[str, Any] = {}


def get_ml_resources() -> Dict[str, Any]:
    """Lazy/cached loader for ML resources."""
    global _ml_resources
    if not _ml_resources:
        # TODO: INTEGRATION POINT - For distributed production, pull model weights, scalers, and performance metrics from an artifact registry or model store (e.g. AWS S3, GCS, or MLflow) with auto-reload capabilities.
        model_path = "model.joblib"
        scaler_path = "scaler.joblib"
        metrics_path = "metrics.json"

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model artifact not found at {model_path}. Run fraud_pipeline.py first.")

        model = joblib.load(model_path)

        if os.path.exists(scaler_path):
            scalers = joblib.load(scaler_path)
        else:
            scalers = None

        if os.path.exists(metrics_path):
            with open(metrics_path, "r") as f:
                metrics = json.load(f)
                threshold = metrics.get("threshold_calibration", {}).get("decision_threshold", 0.67231)
        else:
            threshold = 0.67231

        explainer = shap.TreeExplainer(model)
        feature_names = [f"V{i}" for i in range(1, 29)] + ["scaled_time", "scaled_amount"]

        _ml_resources = {
            "model": model,
            "scalers": scalers,
            "explainer": explainer,
            "decision_threshold": threshold,
            "feature_names": feature_names,
        }
    return _ml_resources


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load ML assets
    get_ml_resources()
    yield
    # Shutdown: Clear cache
    global _ml_resources
    _ml_resources.clear()


app = FastAPI(
    title="RazorPay Real-Time Fraud Scoring & Dispute Evidence API",
    description="Production-ready FastAPI service delivering real-time XGBoost fraud risk scoring with SHAP explainability and automated Visa/Mastercard representment rebuttal PDF generation.",
    version="1.0.0",
    lifespan=lifespan,
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "RazorPay Real-Time Fraud Scoring & Dispute Evidence API",
        "status": "online",
        "version": "1.0.0",
        "endpoints": ["/score-order", "/generate-evidence", "/health"],
    }


@app.get("/health", tags=["Health"])
async def health_check():
    resources = get_ml_resources()
    is_ready = bool(resources and "model" in resources)
    return {
        "status": "healthy" if is_ready else "initializing",
        "model_loaded": is_ready,
        "decision_threshold": resources.get("decision_threshold", 0.67231),
    }


@app.post(
    "/score-order",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    tags=["Fraud Scoring"],
    summary="Real-time XGBoost Risk Scoring & SHAP Attribution",
)
async def score_order(txn: TransactionRequest):
    """
    Evaluates transaction fraud risk using XGBClassifier with scale_pos_weight.
    Returns fraud probability, risk tier, recommended decision action, and top 3 SHAP feature drivers.
    """
    # TODO: INTEGRATION POINT - Log incoming transaction, predicted scores, and inference latency to a secure data stream or monitoring service (e.g. Kafka, Elasticsearch, or Datadog) to track model drift and business metrics.
    resources = get_ml_resources()
    if not resources:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML scoring engine is not initialized.",
        )

    model = resources["model"]
    scalers = resources.get("scalers")
    explainer = resources["explainer"]
    threshold = resources["decision_threshold"]
    feature_names = resources["feature_names"]

    # Scale time & amount
    if scalers:
        scaled_time = float(scalers["time_scaler"].transform(pd.DataFrame([[txn.time]], columns=["Time"]))[0][0])
        scaled_amount = float(scalers["amount_scaler"].transform(pd.DataFrame([[txn.amount]], columns=["Amount"]))[0][0])
    else:
        scaled_time = float(txn.time)
        scaled_amount = float(txn.amount)

    # Construct 30-feature vector: [V1..V28, scaled_time, scaled_amount]
    pca_values = [
        txn.v1, txn.v2, txn.v3, txn.v4, txn.v5, txn.v6, txn.v7, txn.v8,
        txn.v9, txn.v10, txn.v11, txn.v12, txn.v13, txn.v14, txn.v15, txn.v16,
        txn.v17, txn.v18, txn.v19, txn.v20, txn.v21, txn.v22, txn.v23, txn.v24,
        txn.v25, txn.v26, txn.v27, txn.v28,
    ]
    feature_vector = np.array(pca_values + [scaled_time, scaled_amount], dtype=np.float32).reshape(1, -1)

    # 1. Model inference
    probs = model.predict_proba(feature_vector)[0]
    fraud_prob = float(probs[1])

    # 2. Risk Tier & Decision Action Mapping
    if fraud_prob >= 0.85:
        risk_tier = "Critical"
        decision_action = "DECLINE_AND_BLOCK"
    elif fraud_prob >= threshold:
        risk_tier = "High"
        decision_action = "MANUAL_REVIEW_OR_3DS"
    elif fraud_prob >= 0.30:
        risk_tier = "Medium"
        decision_action = "CHALLENGE_3DS"
    else:
        risk_tier = "Low"
        decision_action = "APPROVE_INSTANT"

    is_flagged = fraud_prob >= threshold

    # 3. SHAP Top 3 Drivers
    shap_vals = explainer.shap_values(feature_vector)[0]
    top3_indices = np.argsort(np.abs(shap_vals))[::-1][:3]

    raw_val_lookup = {
        **{f"V{i+1}": pca_values[i] for i in range(28)},
        "scaled_time": scaled_time,
        "scaled_amount": scaled_amount,
    }

    top3_drivers = []
    for idx in top3_indices:
        feat = feature_names[idx]
        val = float(shap_vals[idx])
        direction = "increase_risk" if val > 0 else "decrease_risk"
        top3_drivers.append(
            SHAPDriver(
                feature=feat,
                shap_value=round(val, 6),
                direction=direction,
                feature_value=round(float(raw_val_lookup[feat]), 4),
            )
        )

    return ScoreResponse(
        order_id=txn.order_id or "ORD-ANON",
        fraud_probability=round(fraud_prob, 6),
        risk_tier=risk_tier,
        decision_action=decision_action,
        decision_threshold=round(threshold, 6),
        is_fraud_flagged=is_flagged,
        top3_risk_drivers=top3_drivers,
        model_version="XGBClassifier-v1.0-ScalePosWeight",
    )


@app.post(
    "/generate-evidence",
    status_code=status.HTTP_200_OK,
    tags=["Dispute Representment"],
    summary="Generate Visa/Mastercard Compliant Chargeback Rebuttal PDF",
)
async def generate_evidence(dispute: DisputeEvidenceRequest):
    """
    Generates a formal Visa/Mastercard dispute representment rebuttal PDF packet.
    Returns binary PDF stream ready for direct download or acquirer submission.
    """
    try:
        # TODO: INTEGRATION POINT - Log the dispute case generation request, and backup the generated binary PDF stream to secure persistent object storage (e.g. AWS S3) for transaction/audit logging.
        pdf_bytes = generate_dispute_pdf(dispute)
        filename = f"rebuttal_{dispute.dispute_id}_{dispute.order_id}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf",
                "X-Dispute-ID": dispute.dispute_id,
                "X-Order-ID": dispute.order_id,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dispute PDF: {str(e)}",
        )
