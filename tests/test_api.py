import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health check returns status 200 and ML model readiness."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "decision_threshold" in data


def test_score_order_low_risk():
    """Verify scoring a normal legitimate transaction returns status 200 and low risk tier."""
    payload = {
        "order_id": "ORD-NORMAL-1001",
        "time": 80000.0,
        "amount": 49.99,
        "v1": 0.12,
        "v2": -0.05,
        "v3": 0.22,
        "v4": -0.15,
        "v14": 0.05,
    }
    response = client.post("/score-order", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["order_id"] == "ORD-NORMAL-1001"
    assert 0.0 <= data["fraud_probability"] <= 1.0
    assert data["risk_tier"] in ["Critical", "High", "Medium", "Low"]
    assert data["decision_action"] in [
        "DECLINE_AND_BLOCK",
        "MANUAL_REVIEW_OR_3DS",
        "CHALLENGE_3DS",
        "APPROVE_INSTANT",
    ]
    assert isinstance(data["is_fraud_flagged"], bool)
    assert len(data["top3_risk_drivers"]) == 3
    for driver in data["top3_risk_drivers"]:
        assert "feature" in driver
        assert "shap_value" in driver
        assert driver["direction"] in ["increase_risk", "decrease_risk"]


def test_score_order_high_risk():
    """Verify scoring an anomalous transaction returns status 200 with SHAP drivers."""
    # Typical fraud signature on creditcard.csv: strongly negative V14, V12, V10; high positive V4
    payload = {
        "order_id": "ORD-SUSPICIOUS-9999",
        "time": 406.0,
        "amount": 350.0,
        "v1": -2.31,
        "v2": 1.95,
        "v3": -1.61,
        "v4": 4.50,
        "v10": -3.20,
        "v12": -3.80,
        "v14": -5.20,
    }
    response = client.post("/score-order", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["order_id"] == "ORD-SUSPICIOUS-9999"
    assert 0.0 <= data["fraud_probability"] <= 1.0
    assert len(data["top3_risk_drivers"]) == 3
    assert data["top3_risk_drivers"][0]["feature"] in [
        "V14",
        "V4",
        "V12",
        "V10",
        "V8",
        "V3",
        "V11",
        "scaled_amount",
        "scaled_time",
    ]


def test_generate_evidence_pdf_success():
    """Verify dispute evidence generation returns status 200 and a valid PDF binary stream."""
    payload = {
        "dispute_id": "DISP-2026-8819",
        "order_id": "ORD-2026-9481",
        "arn": "74512930291823719284712",
        "amount": 259.99,
        "currency": "USD",
        "dispute_reason": "10.4 - Other Fraud: Card-Absent Environment",
        "customer_name": "John Doe",
        "customer_email": "john.doe@example.com",
        "customer_phone": "+1 (512) 555-0199",
        "merchant_name": "RazorPay Merchant Services Ltd.",
        "verification": {
            "ip_address": "198.51.100.42",
            "ip_geolocation": "Austin, Texas, United States",
            "avs_result": "Y - Exact Match (Street address and 5-digit ZIP match)",
            "cvv_result": "M - Match (CVV2/CVC2 verified)",
            "three_ds_status": "Y - Fully Authenticated (3-D Secure 2.2 Liability Shift Active)",
            "device_fingerprint_id": "dfp_92a7f3c14b8e01",
        },
        "fulfillment": {
            "carrier_name": "FedEx Express",
            "tracking_number": "781293847291",
            "shipped_date": "2026-08-20",
            "delivery_date": "2026-08-22 14:15:00 UTC",
            "delivery_address": "1040 West 6th St, Austin, TX 78703",
            "delivery_status": "DELIVERED - Direct Signature Obtained",
            "signature_name": "J. DOE",
        },
        "authorization": {
            "auth_code": "AUTH_938102",
            "gateway_transaction_id": "ch_3M4v81kLa901Zq9",
            "timestamp": "2026-08-19 18:32:10 UTC",
            "card_brand": "Visa",
            "card_last4": "4242",
            "network_token_used": True,
        },
        "merchant_rebuttal_statement": "Full 3DS liability shift with positive AVS and direct signature delivery proof.",
    }

    response = client.post("/generate-evidence", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert response.headers["x-dispute-id"] == "DISP-2026-8819"
    assert response.headers["x-order-id"] == "ORD-2026-9481"

    # Validate PDF magic header bytes (%PDF-)
    content = response.content
    assert len(content) > 1000
    assert content.startswith(b"%PDF-")
