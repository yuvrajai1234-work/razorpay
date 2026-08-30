# Real Data Integration TODO Inventory

This document tracks all code-level `TODO` marker locations in the **RazorPay FraudGuard & Dispute Engine** codebase where production data feeds need to be integrated.

---

## 1. Summary of Integration Touchpoints

We have injected corresponding `TODO: INTEGRATION POINT` comments directly into the source code to guide production engineers. Here is the full index of those locations:

### 1.1 Frontend Application Layer
File path: [`frontend/app.py`](file:///c:/Users/yuvra/Coding%20Projects/RazorPay/frontend/app.py)

1.  **API Base Endpoint Configuration**
    *   **Location**: Line 21 (approx)
    *   **Context**: `API_BASE_URL` is currently fallbacked to local port 8000.
    *   **Production Task**: Fetch this from secure environment variables or a configuration vault (e.g. AWS Secrets Manager).

2.  **Dispute Case Queue Retrieval**
    *   **Location**: Line 533 (approx)
    *   **Context**: `mock_disputes` is a static list.
    *   **Production Task**: Replace this mock array with a dynamic SQL query or API request to fetch actual open chargeback disputes from your Postgres database or Gateway Webhooks (Razorpay / Stripe).

3.  **Customer Verification & Logistics Metadata**
    *   **Location**: Line 645 (approx)
    *   **Context**: `pdf_payload` contains hardcoded parameters like IP address, geolocation, shipping dates, AVS result match codes, CVV verification results, and gateway authentication references.
    *   **Production Task**: Wire these arguments to live data stores containing customer session logs (IP, fingerprint), shipping carrier tracks (FedEx, DHL), and credit card network gateways.

---

### 1.2 Backend API Service Layer
File path: [`app/main.py`](file:///c:/Users/yuvra/Coding%20Projects/RazorPay/app/main.py)

1.  **Machine Learning Resource Loading**
    *   **Location**: Line 48 (approx)
    *   **Context**: Models (`model.joblib`), standard scalers (`scaler.joblib`), and calibration metadata (`metrics.json`) are read from local files.
    *   **Production Task**: In a distributed deployment, fetch and cache these files from secure object stores (AWS S3 / GCS) or model registries (MLflow) with asynchronous background check tasks for auto-reloading.

2.  **Transaction Scoring & Diagnostic Logs**
    *   **Location**: Line 143 (approx)
    *   **Context**: `score_order` evaluates request vectors but does not persist predictions.
    *   **Production Task**: Log inputs, probabilities, risk tiers, and timing latencies to high-throughput message buffers (Kafka) or logging services (Datadog, Elasticsearch) to monitor model drift and performance metrics.

3.  **PDF Evidence Storage & Retention**
    *   **Location**: Line 240 (approx)
    *   **Context**: `generate_evidence` compiles report packets and streams them directly, without persistence.
    *   **Production Task**: Write the generated PDF binary streams to a secure cloud bucket (S3) with appropriate access control and audit logging before returning the stream.
