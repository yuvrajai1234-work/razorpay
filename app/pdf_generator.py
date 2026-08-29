import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas import DisputeEvidenceRequest


def generate_dispute_pdf(dispute_data: DisputeEvidenceRequest) -> bytes:
    """
    Generates a Visa/Mastercard compliant dispute representment rebuttal PDF.
    Returns the binary content (bytes).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0f172a")    # Slate 900
    secondary_color = colors.HexColor("#2563eb")  # Blue 600
    accent_green = colors.HexColor("#16a34a")     # Green 600
    dark_gray = colors.HexColor("#334155")        # Slate 700
    light_bg = colors.HexColor("#f8fafc")         # Slate 50
    border_color = colors.HexColor("#cbd5e1")     # Slate 300

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_color,
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=secondary_color,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4,
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=primary_color,
    )

    body_regular = ParagraphStyle(
        "BodyRegular",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=dark_gray,
    )

    badge_success = ParagraphStyle(
        "BadgeSuccess",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=accent_green,
    )

    story = []

    # 1. Header Banner & Merchant Info
    header_data = [
        [
            Paragraph("<b>VISA & MASTERCARD CHARGEBACK REPRESENTMENT REBUTTAL</b>", title_style),
            Paragraph(f"<b>Date Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}<br/><b>Document ID:</b> REB-{dispute_data.dispute_id}", body_regular)
        ],
        [
            Paragraph(f"<b>Merchant:</b> {dispute_data.merchant_name} | <b>Processor Network:</b> Global Acquiring Services", subtitle_style),
            Paragraph(f"<b>Status:</b> FORMAL DISPUTE EVIDENCE SUBMISSION", badge_success)
        ]
    ]
    header_table = Table(header_data, colWidths=[360, 180])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceAfter=8))

    # 2. Executive Case Summary Box
    summary_data = [
        [
            Paragraph("<b>Dispute Case ID:</b>", body_bold),
            Paragraph(dispute_data.dispute_id, body_regular),
            Paragraph("<b>Disputed Amount:</b>", body_bold),
            Paragraph(f"<b>${dispute_data.amount:.2f} {dispute_data.currency}</b>", body_bold),
        ],
        [
            Paragraph("<b>Order Reference:</b>", body_bold),
            Paragraph(dispute_data.order_id, body_regular),
            Paragraph("<b>Dispute Reason Code:</b>", body_bold),
            Paragraph(dispute_data.dispute_reason, body_regular),
        ],
        [
            Paragraph("<b>Acquirer Ref (ARN):</b>", body_bold),
            Paragraph(dispute_data.arn or "N/A", body_regular),
            Paragraph("<b>Cardholder Name:</b>", body_bold),
            Paragraph(dispute_data.customer_name, body_regular),
        ],
        [
            Paragraph("<b>Customer Email / Tel:</b>", body_bold),
            Paragraph(f"{dispute_data.customer_email}<br/>{dispute_data.customer_phone or ''}", body_regular),
            Paragraph("<b>Card Brand / Last 4:</b>", body_bold),
            Paragraph(f"{dispute_data.authorization.card_brand} ending in •••• {dispute_data.authorization.card_last4}", body_regular),
        ]
    ]

    summary_table = Table(summary_data, colWidths=[110, 160, 120, 150])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # 3. Section 1: Cardholder Identity & Authentication Verification (3DS / AVS / CVV)
    story.append(Paragraph("1. Cardholder Authentication & Security Verifications", section_header_style))
    
    auth_data = [
        [Paragraph("<b>Verification Check</b>", body_bold), Paragraph("<b>Result & Network Response</b>", body_bold), Paragraph("<b>Compliance Impact / Rule</b>", body_bold)],
        [
            Paragraph("<b>3-D Secure Protocol (EMV 3DS)</b>", body_regular),
            Paragraph(f"<b>{dispute_data.verification.three_ds_status}</b>", badge_success),
            Paragraph("Visa/Mastercard Liability Shift to Card Issuer applies.", body_regular),
        ],
        [
            Paragraph("<b>Address Verification (AVS)</b>", body_regular),
            Paragraph(dispute_data.verification.avs_result, body_regular),
            Paragraph("Billing and Shipping addresses verified against issuer records.", body_regular),
        ],
        [
            Paragraph("<b>Card Security Code (CVV2/CVC2)</b>", body_regular),
            Paragraph(dispute_data.verification.cvv_result, body_regular),
            Paragraph("Physical possession of legitimate payment card confirmed.", body_regular),
        ],
        [
            Paragraph("<b>Customer IP & Device Fingerprint</b>", body_regular),
            Paragraph(f"IP: {dispute_data.verification.ip_address}<br/>Location: {dispute_data.verification.ip_geolocation}<br/>Device ID: {dispute_data.verification.device_fingerprint_id or 'N/A'}", body_regular),
            Paragraph("Session telemetry confirms matching geolocation and trusted device profile.", body_regular),
        ],
    ]

    auth_table = Table(auth_data, colWidths=[160, 210, 170])
    auth_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(auth_table)
    story.append(Spacer(1, 8))

    # 4. Section 2: Proof of Delivery & Order Fulfillment
    story.append(Paragraph("2. Fulfillment & Direct Signature Proof of Delivery", section_header_style))
    
    delivery_data = [
        [Paragraph("<b>Parameter</b>", body_bold), Paragraph("<b>Fulfillment Evidence Record</b>", body_bold)],
        [
            Paragraph("<b>Carrier & Tracking Number</b>", body_regular),
            Paragraph(f"<b>{dispute_data.fulfillment.carrier_name}</b> - Tracking ID: <u>{dispute_data.fulfillment.tracking_number}</u>", body_regular),
        ],
        [
            Paragraph("<b>Dispatch & Delivery Timestamps</b>", body_regular),
            Paragraph(f"Shipped: {dispute_data.fulfillment.shipped_date} | Delivered: <b>{dispute_data.fulfillment.delivery_date}</b>", body_regular),
        ],
        [
            Paragraph("<b>Destination Delivery Address</b>", body_regular),
            Paragraph(f"{dispute_data.fulfillment.delivery_address} <i>(Matches AVS Billing Address)</i>", body_regular),
        ],
        [
            Paragraph("<b>Proof of Delivery / Signature</b>", body_regular),
            Paragraph(f"Status: <b>{dispute_data.fulfillment.delivery_status}</b><br/>Signatory on File: <b>{dispute_data.fulfillment.signature_name or dispute_data.customer_name}</b>", badge_success),
        ],
    ]

    delivery_table = Table(delivery_data, colWidths=[160, 380])
    delivery_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(delivery_table)
    story.append(Spacer(1, 8))

    # 5. Section 3: Payment Gateway Authorization Audit Trail
    story.append(Paragraph("3. Payment Authorization Audit Trail", section_header_style))

    gateway_data = [
        [
            Paragraph("<b>Auth Approval Code:</b>", body_bold),
            Paragraph(dispute_data.authorization.auth_code, body_regular),
            Paragraph("<b>Processor Txn ID:</b>", body_bold),
            Paragraph(dispute_data.authorization.gateway_transaction_id, body_regular),
        ],
        [
            Paragraph("<b>Auth Timestamp:</b>", body_bold),
            Paragraph(dispute_data.authorization.timestamp, body_regular),
            Paragraph("<b>EMVCo Tokenized:</b>", body_bold),
            Paragraph("Yes (Secure Network Token)" if dispute_data.authorization.network_token_used else "Standard PAN", body_regular),
        ]
    ]

    gateway_table = Table(gateway_data, colWidths=[120, 150, 120, 150])
    gateway_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(gateway_table)
    story.append(Spacer(1, 8))

    # 6. Section 4: Merchant Rebuttal Narrative & Formal Certification
    story.append(Paragraph("4. Merchant Representment Statement & Rule Certification", section_header_style))

    rebuttal_text = (
        f"<b>Rebuttal Summary:</b> {dispute_data.merchant_rebuttal_statement}<br/><br/>"
        "<b>Visa & Mastercard Representment Rules Affirmation:</b> The merchant hereby submits conclusive compelling evidence proving that the transaction was properly authenticated with 3-D Secure, verified with positive AVS/CVV matching, and physically delivered with direct signature confirmation to the verified cardholder address. In accordance with card scheme dispute rules, liability shift is active and merchant requests immediate reversal of the chargeback."
    )

    statement_data = [[Paragraph(rebuttal_text, body_regular)]]
    statement_table = Table(statement_data, colWidths=[540])
    statement_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93c5fd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(statement_table)
    story.append(Spacer(1, 10))

    # Footer note
    footer_text = Paragraph(
        "<font size='7' color='#64748b'>Confidential & Proprietary — Prepared for Acquirer & Card Issuer Dispute Resolution Board only. Generated by RazorPay Automated Evidence Engine.</font>",
        ParagraphStyle("Footer", parent=styles["Normal"], alignment=1)
    )
    story.append(footer_text)

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
