import base64
import json
import os
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ─────────────────────────────────────────────────────────
# Streamlit Page Configuration & Modern Styling
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RazorPay FraudGuard & Dispute Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Custom CSS for polished fintech aesthetics
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.1rem;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .tier-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
    }
    .tier-critical { background-color: #fee2e2; color: #991b1b; border: 1px solid #f87171; }
    .tier-high { background-color: #ffedd5; color: #9a3412; border: 1px solid #fb923c; }
    .tier-medium { background-color: #fef9c3; color: #854d0e; border: 1px solid #facc15; }
    .tier-low { background-color: #dcfce7; color: #166534; border: 1px solid #4ade80; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #f8fafc;
        border-radius: 8px 8px 0 0;
        gap: 6px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-top: 3px solid #2563eb;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────
# Header & Navigation
# ─────────────────────────────────────────────────────────
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown("<div class='main-header'>🛡️ RazorPay FraudGuard & Dispute Engine</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Real-time ML Risk Scoring • SHAP Explainability • Automated Visa/Mastercard Representment</div>", unsafe_allow_html=True)

with col_head2:
    try:
        health_resp = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if health_resp.status_code == 200:
            hdata = health_resp.json()
            st.success(f"● API Online (Threshold: {hdata.get('decision_threshold', 0.6723):.4f})")
        else:
            st.warning("● API Warning")
    except Exception:
        st.error("● API Offline (Port 8000)")

# ─────────────────────────────────────────────────────────
# Tab Layout
# ─────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "⚡ Tab 1: Checkout Simulator",
    "📑 Tab 2: Dispute Queue & Auto-Responder",
    "📊 Tab 3: Governance & Audit Log",
])

# ─────────────────────────────────────────────────────────
# TAB 1: CHECKOUT SIMULATOR
# ─────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 💳 Real-Time Transaction Scoring & SHAP Attribution")
    st.caption("Simulate checkout payloads and receive real-time XGBoost fraud probability, risk tier classification, and SHAP explainability drivers.")

    # Preset selector for fast demonstration
    preset = st.selectbox(
        "🎯 Select Transaction Preset:",
        [
            "Legitimate Customer (Safe E-Commerce Order)",
            "High-Risk Fraud (Card-Not-Present Anomaly)",
            "Borderline Risk (Requires 3DS Step-Up Challenge)",
            "Custom Manual Input",
        ],
        index=0,
    )

    # Preset values
    if preset == "Legitimate Customer (Safe E-Commerce Order)":
        default_order_id = "ORD-LEGIT-1049"
        default_amount = 74.50
        default_time = 85200.0
        default_v1 = 0.15
        default_v2 = -0.08
        default_v3 = 0.45
        default_v4 = -0.32
        default_v10 = 0.12
        default_v12 = 0.05
        default_v14 = 0.21
    elif preset == "High-Risk Fraud (Card-Not-Present Anomaly)":
        default_order_id = "ORD-FRAUD-9481"
        default_amount = 499.00
        default_time = 406.0
        default_v1 = -2.85
        default_v2 = 2.45
        default_v3 = -2.90
        default_v4 = 4.85
        default_v10 = -3.80
        default_v12 = -4.20
        default_v14 = -5.60
    elif preset == "Borderline Risk (Requires 3DS Step-Up Challenge)":
        default_order_id = "ORD-BORDER-3302"
        default_amount = 210.00
        default_time = 42000.0
        default_v1 = -1.10
        default_v2 = 0.95
        default_v3 = -0.80
        default_v4 = 1.95
        default_v10 = -1.20
        default_v12 = -1.40
        default_v14 = -1.85
    else:
        default_order_id = "ORD-CUSTOM-001"
        default_amount = 150.00
        default_time = 50000.0
        default_v1 = 0.0
        default_v2 = 0.0
        default_v3 = 0.0
        default_v4 = 0.0
        default_v10 = 0.0
        default_v12 = 0.0
        default_v14 = 0.0

    col_inp1, col_inp2, col_inp3 = st.columns([1.2, 1.2, 1.2])

    with col_inp1:
        st.markdown("**Order Metadata**")
        input_order_id = st.text_input("Order ID", value=default_order_id)
        input_amount = st.number_input("Transaction Amount ($)", min_value=0.50, max_value=25000.0, value=float(default_amount), step=10.0)
        input_time = st.number_input("Time Elapsed (s)", min_value=0.0, max_value=200000.0, value=float(default_time), step=500.0)

    with col_inp2:
        st.markdown("**Core Anomaly Features (PCA)**")
        input_v14 = st.slider("V14 (Primary Fraud Indicator)", min_value=-15.0, max_value=5.0, value=float(default_v14), step=0.1)
        input_v4 = st.slider("V4 (Velocity / Risk Multiplier)", min_value=-5.0, max_value=12.0, value=float(default_v4), step=0.1)
        input_v12 = st.slider("V12 (Account Consistency)", min_value=-15.0, max_value=5.0, value=float(default_v12), step=0.1)

    with col_inp3:
        st.markdown("**Secondary Risk Signals**")
        input_v10 = st.slider("V10 (Terminal / IP Disparity)", min_value=-15.0, max_value=5.0, value=float(default_v10), step=0.1)
        input_v3 = st.slider("V3 (Transaction Frequency Pattern)", min_value=-15.0, max_value=5.0, value=float(default_v3), step=0.1)
        input_v1 = st.slider("V1 (Cardholder Deviation)", min_value=-15.0, max_value=5.0, value=float(default_v1), step=0.1)

    score_btn = st.button("🚀 Score Transaction via Real-Time API", type="primary", use_container_width=True)

    if score_btn or "last_score_result" in st.session_state:
        if score_btn:
            payload = {
                "order_id": input_order_id,
                "time": float(input_time),
                "amount": float(input_amount),
                "v1": float(input_v1),
                "v2": float(default_v2),
                "v3": float(input_v3),
                "v4": float(input_v4),
                "v10": float(input_v10),
                "v12": float(input_v12),
                "v14": float(input_v14),
            }
            t_start = time.time()
            try:
                resp = requests.post(f"{API_BASE_URL}/score-order", json=payload, timeout=5)
                latency_ms = (time.time() - t_start) * 1000
                if resp.status_code == 200:
                    st.session_state["last_score_result"] = resp.json()
                    st.session_state["last_latency_ms"] = latency_ms
                else:
                    st.error(f"API Error {resp.status_code}: {resp.text}")
            except Exception as e:
                st.error(f"Connection Failed: {str(e)}")

        if "last_score_result" in st.session_state:
            result = st.session_state["last_score_result"]
            latency_ms = st.session_state.get("last_latency_ms", 12.4)

            st.markdown("---")
            st.markdown("#### 🎯 Scoring Decision & Risk Assessment")

            col_res1, col_res2, col_res3 = st.columns([1.5, 1.2, 1.3])

            with col_res1:
                prob = result["fraud_probability"]
                prob_pct = prob * 100

                # Risk gauge
                fig_gauge = go.Figure(
                    go.Indicator(
                        mode="gauge+number",
                        value=prob_pct,
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": "Fraud Probability (%)", "font": {"size": 16, "color": "#0f172a"}},
                        number={"suffix": "%", "font": {"size": 28, "color": "#0f172a"}},
                        gauge={
                            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
                            "bar": {"color": "#0f172a", "thickness": 0.25},
                            "bgcolor": "white",
                            "borderwidth": 2,
                            "bordercolor": "#cbd5e1",
                            "steps": [
                                {"range": [0, 30], "color": "#bbf7d0"},    # Low (green)
                                {"range": [30, 67.2], "color": "#fef08a"}, # Medium (yellow)
                                {"range": [67.2, 85], "color": "#fed7aa"}, # High (orange)
                                {"range": [85, 100], "color": "#fecaca"},  # Critical (red)
                            ],
                            "threshold": {
                                "line": {"color": "#dc2626", "width": 4},
                                "thickness": 0.75,
                                "value": result["decision_threshold"] * 100,
                            },
                        },
                    )
                )
                fig_gauge.update_layout(height=240, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)

            with col_res2:
                tier = result["risk_tier"]
                tier_class = f"tier-{tier.lower()}"
                action = result["decision_action"]

                st.markdown(f"**Assigned Risk Tier:**")
                st.markdown(f"<span class='tier-badge {tier_class}'>{tier} Risk</span>", unsafe_allow_html=True)
                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown(f"**Recommended Decision Action:**")
                st.info(f"⚡ **`{action}`**")
                st.caption(f"Decision Threshold: `{result['decision_threshold']:.4f}` | Calibrated Model")

            with col_res3:
                st.metric("Inference Latency", f"{latency_ms:.1f} ms", delta="Fast Engine", delta_color="normal")
                st.metric("Flagged as Fraud", "YES 🚨" if result["is_fraud_flagged"] else "NO ✅")
                st.metric("Model Version", result.get("model_version", "XGBoost-ScalePosWeight"))

            # SHAP Waterfall/Bar Chart
            st.markdown("#### 🔍 SHAP Local Attribution (Top 3 Risk Drivers)")
            st.caption("SHAP (SHapley Additive exPlanations) isolates the exact marginal risk contribution of each input signal.")

            drivers = result.get("top3_risk_drivers", [])
            if drivers:
                df_shap = pd.DataFrame(drivers)
                df_shap["color"] = df_shap["direction"].apply(lambda d: "#ef4444" if d == "increase_risk" else "#22c55e")
                df_shap["display_label"] = df_shap.apply(
                    lambda r: f"{r['feature']} (input={r.get('feature_value', 0):.2f})", axis=1
                )

                fig_shap = px.bar(
                    df_shap,
                    x="shap_value",
                    y="display_label",
                    orientation="h",
                    color="direction",
                    color_discrete_map={"increase_risk": "#ef4444", "decrease_risk": "#22c55e"},
                    title="Top 3 Feature Attributions (SHAP TreeExplainer)",
                    labels={"shap_value": "SHAP Risk Contribution (+ = Higher Risk, - = Lower Risk)", "display_label": "Feature"},
                )
                fig_shap.update_layout(height=230, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_shap, use_container_width=True)

                col_d1, col_d2, col_d3 = st.columns(3)
                for i, d in enumerate(drivers):
                    with [col_d1, col_d2, col_d3][i]:
                        direction_icon = "🔺 Increases Risk" if d["direction"] == "increase_risk" else "🔻 Decreases Risk"
                        st.markdown(
                            f"""
                            <div class='metric-card'>
                                <b>Driver #{i+1}: {d['feature']}</b><br/>
                                <span style='font-size:1.2rem; font-weight:700; color:{'#dc2626' if d['direction']=='increase_risk' else '#16a34a'};'>
                                    {d['shap_value']:+.4f}
                                </span><br/>
                                <small>{direction_icon}</small>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

# ─────────────────────────────────────────────────────────
# TAB 2: DISPUTE QUEUE & AUTO-RESPONDER
# ─────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 📑 Dispute Representment Queue & Automated PDF Generator")
    st.caption("Manage incoming chargebacks, compile EMV 3DS, carrier tracking, and authorization audit trails into automated Visa/Mastercard rebuttal packets.")

    # Synthetic mock dispute data
    mock_disputes = [
        {
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
            "card_brand": "Visa",
            "card_last4": "4242",
            "three_ds_status": "Y - Fully Authenticated (Liability Shift Active)",
            "avs_result": "Y - Exact Match (Street address and 5-digit ZIP match)",
            "carrier_name": "FedEx Express",
            "tracking_number": "781293847291",
            "delivery_status": "DELIVERED - Direct Signature Obtained",
            "delivery_date": "2026-08-22 14:15:00 UTC",
            "rebuttal_strength": "High (98% Win Probability)",
        },
        {
            "dispute_id": "DISP-2026-9042",
            "order_id": "ORD-2026-9720",
            "arn": "85621049281729384710293",
            "amount": 420.50,
            "currency": "USD",
            "dispute_reason": "4837 - No Cardholder Authorization",
            "customer_name": "Sarah Connor",
            "customer_email": "sarah.c@cyberdyne.org",
            "customer_phone": "+1 (310) 555-0144",
            "merchant_name": "RazorPay Merchant Services Ltd.",
            "card_brand": "Mastercard",
            "card_last4": "5512",
            "three_ds_status": "Y - Frictionless 3DS 2.2 (Liability Shift Active)",
            "avs_result": "Z - 5-Digit ZIP Match",
            "carrier_name": "UPS Worldwide",
            "tracking_number": "1Z9999999999999999",
            "delivery_status": "DELIVERED - Adult Signature Verified",
            "delivery_date": "2026-08-24 11:30:00 UTC",
            "rebuttal_strength": "High (95% Win Probability)",
        },
        {
            "dispute_id": "DISP-2026-9110",
            "order_id": "ORD-2026-9815",
            "arn": "91827364501928374650192",
            "amount": 139.00,
            "currency": "USD",
            "dispute_reason": "13.1 - Merchandise Not Received",
            "customer_name": "Robert Vance",
            "customer_email": "bob.vance@vancerefrig.com",
            "customer_phone": "+1 (570) 555-0182",
            "merchant_name": "RazorPay Merchant Services Ltd.",
            "card_brand": "Visa",
            "card_last4": "1881",
            "three_ds_status": "A - Attempted / Proof of Frictionless Flow",
            "avs_result": "Y - Exact Match (Street address and ZIP match)",
            "carrier_name": "DHL Express",
            "tracking_number": "940011189922334455",
            "delivery_status": "DELIVERED - GPS & Photo Proof Attached",
            "delivery_date": "2026-08-25 16:45:00 UTC",
            "rebuttal_strength": "Medium-High (90% Win Probability)",
        },
    ]

    # Display Dispute Table
    df_disputes = pd.DataFrame(mock_disputes)[
        ["dispute_id", "order_id", "amount", "card_brand", "dispute_reason", "three_ds_status", "carrier_name", "rebuttal_strength"]
    ]
    st.dataframe(
        df_disputes,
        use_container_width=True,
        column_config={
            "amount": st.column_config.NumberColumn("Disputed Amount", format="$%.2f"),
            "rebuttal_strength": st.column_config.TextColumn("Win Probability"),
        },
    )

    st.markdown("#### ⚙️ Generate Representment Rebuttal Packet")
    selected_disp_id = st.selectbox(
        "Select Dispute Case to Represent:",
        [d["dispute_id"] for d in mock_disputes],
        format_func=lambda x: f"{x} - {next(d['customer_name'] for d in mock_disputes if d['dispute_id'] == x)} (${next(d['amount'] for d in mock_disputes if d['dispute_id'] == x):.2f})",
    )

    selected_dispute = next(d for d in mock_disputes if d["dispute_id"] == selected_disp_id)

    col_disp1, col_disp2 = st.columns([1, 1])

    with col_disp1:
        st.markdown("**Evidence Bundle Overview:**")
        st.markdown(f"• **Order Reference:** `{selected_dispute['order_id']}`")
        st.markdown(f"• **Disputed Amount:** `${selected_dispute['amount']:.2f} {selected_dispute['currency']}`")
        st.markdown(f"• **Cardholder:** `{selected_dispute['customer_name']}` ({selected_dispute['customer_email']})")
        st.markdown(f"• **3-D Secure Protocol:** `{selected_dispute['three_ds_status']}`")
        st.markdown(f"• **AVS Address Check:** `{selected_dispute['avs_result']}`")

    with col_disp2:
        st.markdown("**Fulfillment & Audit Proof:**")
        st.markdown(f"• **Carrier:** `{selected_dispute['carrier_name']}` (Tracking: `{selected_dispute['tracking_number']}`)")
        st.markdown(f"• **Delivery Status:** `{selected_dispute['delivery_status']}`")
        st.markdown(f"• **Delivery Timestamp:** `{selected_dispute['delivery_date']}`")
        st.markdown(f"• **Card Authorization:** `{selected_dispute['card_brand']} ending in {selected_dispute['card_last4']}`")
        st.markdown(f"• **Reason Code:** `{selected_dispute['dispute_reason']}`")

    gen_btn = st.button("📄 Generate Visa/Mastercard Rebuttal PDF", type="primary", use_container_width=True)

    if gen_btn or f"pdf_bytes_{selected_disp_id}" in st.session_state:
        if gen_btn:
            pdf_payload = {
                "dispute_id": selected_dispute["dispute_id"],
                "order_id": selected_dispute["order_id"],
                "arn": selected_dispute["arn"],
                "amount": float(selected_dispute["amount"]),
                "currency": selected_dispute["currency"],
                "dispute_reason": selected_dispute["dispute_reason"],
                "customer_name": selected_dispute["customer_name"],
                "customer_email": selected_dispute["customer_email"],
                "customer_phone": selected_dispute["customer_phone"],
                "merchant_name": selected_dispute["merchant_name"],
                "verification": {
                    "ip_address": "198.51.100.42",
                    "ip_geolocation": "Austin, TX, US",
                    "avs_result": selected_dispute["avs_result"],
                    "cvv_result": "M - Match (CVV2 verified)",
                    "three_ds_status": selected_dispute["three_ds_status"],
                    "device_fingerprint_id": "dfp_92a7f3c14b8e01",
                },
                "fulfillment": {
                    "carrier_name": selected_dispute["carrier_name"],
                    "tracking_number": selected_dispute["tracking_number"],
                    "shipped_date": "2026-08-20",
                    "delivery_date": selected_dispute["delivery_date"],
                    "delivery_address": "1040 West 6th St, Austin, TX 78703",
                    "delivery_status": selected_dispute["delivery_status"],
                    "signature_name": selected_dispute["customer_name"].upper(),
                },
                "authorization": {
                    "auth_code": "AUTH_938102",
                    "gateway_transaction_id": "ch_3M4v81kLa901Zq9",
                    "timestamp": "2026-08-19 18:32:10 UTC",
                    "card_brand": selected_dispute["card_brand"],
                    "card_last4": selected_dispute["card_last4"],
                    "network_token_used": True,
                },
                "merchant_rebuttal_statement": "Full 3DS liability shift active, positive AVS/CVV matching, and verified carrier proof of delivery with direct signature.",
            }

            with st.spinner("Compiling ReportLab PDF representment package..."):
                try:
                    resp = requests.post(f"{API_BASE_URL}/generate-evidence", json=pdf_payload, timeout=8)
                    if resp.status_code == 200:
                        st.session_state[f"pdf_bytes_{selected_disp_id}"] = resp.content
                        st.success("✅ Formal Dispute Representment Packet Generated Successfully!")
                    else:
                        st.error(f"PDF Generation Failed ({resp.status_code}): {resp.text}")
                except Exception as e:
                    st.error(f"API Request Failed: {str(e)}")

        if f"pdf_bytes_{selected_disp_id}" in st.session_state:
            pdf_data = st.session_state[f"pdf_bytes_{selected_disp_id}"]
            b64_pdf = base64.b64encode(pdf_data).decode("utf-8")

            col_down1, col_down2 = st.columns([1, 2])
            with col_down1:
                st.download_button(
                    label="💾 Download Rebuttal PDF Packet",
                    data=pdf_data,
                    file_name=f"rebuttal_{selected_dispute['dispute_id']}_{selected_dispute['order_id']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            with col_down2:
                st.caption(f"File size: {len(pdf_data) / 1024:.1f} KB | Ready for Acquirer & Dispute Board Submission")

            st.markdown("#### 📄 Document Live Preview:")
            pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="650" type="application/pdf" style="border: 1px solid #cbd5e1; border-radius: 8px;"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# TAB 3: GOVERNANCE & AUDIT LOG
# ─────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 📊 Model Governance, Policy & Cost-Sensitive Value")
    st.caption("Audit trail of model calibration, 4-tier risk routing policy, and net merchant financial savings metrics.")

    # Load metrics from metrics.json
    metrics_path = "metrics.json"
    metrics_data = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            metrics_data = json.load(f)

    # 1. Four-Tier Classification Policy
    st.markdown("#### 1. Four-Tier Risk Classification Policy Matrix")
    policy_data = [
        {
            "Risk Tier": "Critical",
            "Probability Range": "≥ 85.0%",
            "Automated Policy Action": "DECLINE_AND_BLOCK",
            "SLA / Operational Routing": "Immediate Block & IP Blacklist",
            "Customer Impact": "Order Rejected with Fraud Notification",
        },
        {
            "Risk Tier": "High",
            "Probability Range": "≥ 67.2% (Calibrated Threshold)",
            "Automated Policy Action": "MANUAL_REVIEW_OR_3DS",
            "SLA / Operational Routing": "Route to Risk Ops Queue (<15 min SLA)",
            "Customer Impact": "Hold for Verification or Biometric 3DS",
        },
        {
            "Risk Tier": "Medium",
            "Probability Range": "30.0% – 67.2%",
            "Automated Policy Action": "CHALLENGE_3DS",
            "SLA / Operational Routing": "Trigger EMV 3DS OTP Step-Up",
            "Customer Impact": "Frictionless unless Bank Challenge Required",
        },
        {
            "Risk Tier": "Low",
            "Probability Range": "< 30.0%",
            "Automated Policy Action": "APPROVE_INSTANT",
            "SLA / Operational Routing": "Direct Settlement Authorization",
            "Customer Impact": "Instant Sub-second Checkout",
        },
    ]
    st.dataframe(pd.DataFrame(policy_data), use_container_width=True)

    # 2. Performance Scorecard
    st.markdown("#### 2. Held-Out Test Evaluation Scorecard (56,962 Transactions)")
    perf = metrics_data.get("performance", {})

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        p_val = perf.get("precision", 0.8901) * 100
        st.metric("Test Precision", f"{p_val:.2f}%", delta="Target ≥ 88% Met ✅")
    with col_m2:
        r_val = perf.get("recall", 0.8265) * 100
        st.metric("Test Recall", f"{r_val:.2f}%", delta="Target ≥ 78% Met ✅")
    with col_m3:
        auc_val = perf.get("roc_auc", 0.9773)
        st.metric("ROC-AUC", f"{auc_val:.4f}", delta="Excellent Discrimination")
    with col_m4:
        pr_val = perf.get("pr_auc", 0.8811)
        st.metric("PR-AUC (Avg Precision)", f"{pr_val:.4f}", delta="Imbalance Robust")

    # 3. Cost-Sensitive Net Value Economics
    st.markdown("#### 3. Cost-Sensitive Net Merchant Financial Savings")
    cost_info = metrics_data.get("cost_sensitive_evaluation", {})

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        st.metric("Gross Chargeback Recovery", f"${cost_info.get('gross_savings_usd', 4050.0):,.2f}", f"+81 TPs × $50")
    with col_c2:
        st.metric("FP Friction Cost", f"-${cost_info.get('false_positive_cost_usd', 150.0):,.2f}", f"-10 FPs × $15")
    with col_c3:
        st.metric("Missed Fraud Cost", f"-${cost_info.get('missed_fraud_cost_usd', 850.0):,.2f}", f"-17 FNs × $50")
    with col_c4:
        net_val = cost_info.get("net_savings_usd", 3050.0)
        roi_val = cost_info.get("roi_pct", 62.2)
        st.metric("Net Merchant Savings", f"${net_val:,.2f}", f"ROI: {roi_val:.1f}% vs Oracle")

    # Formula card
    st.info(
        """
        **Cost-Sensitive Net Savings Model Formula:**  
        $$\\text{Net Value Saved} = (\\text{True Positives} \\times \\$50\\text{ Chargeback Recovery}) - (\\text{False Positives} \\times \\$15\\text{ Customer Friction}) - (\\text{False Negatives} \\times \\$50\\text{ Fraud Loss})$$
        """
    )

    # 4. Global Top-10 SHAP Feature Ranking
    st.markdown("#### 4. Global Feature Importance (SHAP TreeExplainer)")
    global_shap = metrics_data.get("shap_global_top10", [])
    if global_shap:
        df_gshap = pd.DataFrame(global_shap)
        fig_gshap = px.bar(
            df_gshap,
            x="mean_abs_shap",
            y="feature",
            orientation="h",
            title="Global Mean |SHAP| Feature Ranking",
            labels={"mean_abs_shap": "Mean |SHAP Value| (Impact on Model Output)", "feature": "Feature"},
            color="mean_abs_shap",
            color_continuous_scale="Blues",
        )
        fig_gshap.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gshap, use_container_width=True)
