from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TransactionRequest(BaseModel):
    order_id: Optional[str] = Field(default="ORD-SAMPLE-001", description="Unique identifier for order/transaction")
    time: float = Field(..., description="Seconds elapsed since first transaction in dataset")
    amount: float = Field(..., description="Transaction amount in USD")
    v1: float = Field(default=0.0, description="PCA feature V1")
    v2: float = Field(default=0.0, description="PCA feature V2")
    v3: float = Field(default=0.0, description="PCA feature V3")
    v4: float = Field(default=0.0, description="PCA feature V4")
    v5: float = Field(default=0.0, description="PCA feature V5")
    v6: float = Field(default=0.0, description="PCA feature V6")
    v7: float = Field(default=0.0, description="PCA feature V7")
    v8: float = Field(default=0.0, description="PCA feature V8")
    v9: float = Field(default=0.0, description="PCA feature V9")
    v10: float = Field(default=0.0, description="PCA feature V10")
    v11: float = Field(default=0.0, description="PCA feature V11")
    v12: float = Field(default=0.0, description="PCA feature V12")
    v13: float = Field(default=0.0, description="PCA feature V13")
    v14: float = Field(default=0.0, description="PCA feature V14")
    v15: float = Field(default=0.0, description="PCA feature V15")
    v16: float = Field(default=0.0, description="PCA feature V16")
    v17: float = Field(default=0.0, description="PCA feature V17")
    v18: float = Field(default=0.0, description="PCA feature V18")
    v19: float = Field(default=0.0, description="PCA feature V19")
    v20: float = Field(default=0.0, description="PCA feature V20")
    v21: float = Field(default=0.0, description="PCA feature V21")
    v22: float = Field(default=0.0, description="PCA feature V22")
    v23: float = Field(default=0.0, description="PCA feature V23")
    v24: float = Field(default=0.0, description="PCA feature V24")
    v25: float = Field(default=0.0, description="PCA feature V25")
    v26: float = Field(default=0.0, description="PCA feature V26")
    v27: float = Field(default=0.0, description="PCA feature V27")
    v28: float = Field(default=0.0, description="PCA feature V28")

    model_config = {
        "json_schema_extra": {
            "example": {
                "order_id": "ORD-2026-9481",
                "time": 406.0,
                "amount": 259.99,
                "v1": -2.312226542,
                "v2": 1.951992011,
                "v3": -1.609850732,
                "v4": 3.997905588,
                "v14": -2.840541064,
            }
        }
    }


class SHAPDriver(BaseModel):
    feature: str = Field(..., description="Feature name")
    shap_value: float = Field(..., description="SHAP attribution value")
    direction: str = Field(..., description="'increase_risk' or 'decrease_risk'")
    feature_value: Optional[float] = Field(None, description="Actual input value")


class ScoreResponse(BaseModel):
    order_id: str
    fraud_probability: float = Field(..., description="Predicted probability of fraud [0.0 - 1.0]")
    risk_tier: str = Field(..., description="Critical, High, Medium, Low")
    decision_action: str = Field(..., description="DECLINE_AND_BLOCK, MANUAL_REVIEW_OR_3DS, CHALLENGE_3DS, APPROVE_INSTANT")
    decision_threshold: float = Field(..., description="Calibrated decision threshold")
    is_fraud_flagged: bool = Field(..., description="True if probability >= decision_threshold")
    top3_risk_drivers: List[SHAPDriver] = Field(..., description="Top 3 SHAP feature drivers")
    model_version: str = Field(default="XGBClassifier-v1.0")


class CustomerVerification(BaseModel):
    ip_address: str = Field(default="198.51.100.42", description="Customer IPv4/IPv6 address")
    ip_geolocation: str = Field(default="Austin, Texas, United States", description="City, State, Country")
    avs_result: str = Field(default="Y - Exact Match (Street address and 5-digit ZIP match)", description="Address Verification Service response code/description")
    cvv_result: str = Field(default="M - Match (CVV2/CVC2 verified)", description="Card verification value check")
    three_ds_status: str = Field(default="Y - Fully Authenticated (3-D Secure 2.2 Liability Shift Active)", description="3DS protocol authentication result")
    device_fingerprint_id: Optional[str] = Field(default="dfp_92a7f3c14b8e01", description="Device ID / browser fingerprint hash")


class CarrierFulfillment(BaseModel):
    carrier_name: str = Field(default="FedEx Express", description="Fulfillment carrier")
    tracking_number: str = Field(default="781293847291", description="Carrier shipment tracking ID")
    shipped_date: str = Field(default="2026-08-20", description="Dispatch date")
    delivery_date: str = Field(default="2026-08-22 14:15:00 UTC", description="Proof of delivery timestamp")
    delivery_address: str = Field(default="1040 West 6th St, Austin, TX 78703", description="Physical destination matching billing/shipping AVS")
    delivery_status: str = Field(default="DELIVERED - Direct Signature Obtained", description="Carrier confirmation status")
    signature_name: Optional[str] = Field(default="J. DOE", description="Signatory name from carrier scan")


class AuthorizationAudit(BaseModel):
    auth_code: str = Field(default="AUTH_938102", description="Card issuing bank authorization approval code")
    gateway_transaction_id: str = Field(default="ch_3M4v81kLa901Zq9", description="Payment processor transaction identifier")
    timestamp: str = Field(default="2026-08-19 18:32:10 UTC", description="Authorization transaction timestamp")
    card_brand: str = Field(default="Visa", description="Payment card network (Visa, Mastercard, Amex)")
    card_last4: str = Field(default="4242", description="Last 4 digits of card number")
    network_token_used: bool = Field(default=True, description="True if EMVCo network token was processed")


class DisputeEvidenceRequest(BaseModel):
    dispute_id: str = Field(default="DISP-2026-8819", description="Acquirer/Network dispute case ID")
    order_id: str = Field(default="ORD-2026-9481", description="Merchant order reference")
    arn: Optional[str] = Field(default="74512930291823719284712", description="Acquirer Reference Number")
    amount: float = Field(default=259.99, description="Disputed amount")
    currency: str = Field(default="USD", description="Three-letter ISO currency code")
    dispute_reason: str = Field(default="10.4 - Other Fraud: Card-Absent Environment", description="Visa/Mastercard reason code")
    customer_name: str = Field(default="John Doe", description="Cardholder name")
    customer_email: str = Field(default="john.doe@example.com", description="Customer email on record")
    customer_phone: Optional[str] = Field(default="+1 (512) 555-0199", description="Customer contact number")
    merchant_name: str = Field(default="RazorPay Merchant Services Ltd.", description="Registered merchant business name")
    verification: CustomerVerification = Field(default_factory=CustomerVerification)
    fulfillment: CarrierFulfillment = Field(default_factory=CarrierFulfillment)
    authorization: AuthorizationAudit = Field(default_factory=AuthorizationAudit)
    merchant_rebuttal_statement: Optional[str] = Field(
        default="Cardholder placed order with full 3DS liability shift, matched AVS/CVV, and order was successfully fulfilled with direct signature proof.",
        description="Executive summary statement for issuer review"
    )
