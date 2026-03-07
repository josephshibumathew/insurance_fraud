"""PDF rendering utilities for fraud analysis reports."""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .response_parser import extract_recommendations

DISCLAIMER = "This report is AI-generated and should be reviewed by a qualified insurance professional"


def _load_reportlab_components() -> dict[str, Any]:
    try:
        shapes = importlib.import_module("reportlab.graphics.shapes")
        lib = importlib.import_module("reportlab.lib")
        pagesizes = importlib.import_module("reportlab.lib.pagesizes")
        styles = importlib.import_module("reportlab.lib.styles")
        units = importlib.import_module("reportlab.lib.units")
        platypus = importlib.import_module("reportlab.platypus")
    except Exception as exc:
        raise ImportError("reportlab is required for PDF generation. Install with `pip install reportlab`.") from exc

    return {
        "Drawing": getattr(shapes, "Drawing"),
        "Rect": getattr(shapes, "Rect"),
        "String": getattr(shapes, "String"),
        "colors": getattr(lib, "colors"),
        "letter": getattr(pagesizes, "letter"),
        "ParagraphStyle": getattr(styles, "ParagraphStyle"),
        "getSampleStyleSheet": getattr(styles, "getSampleStyleSheet"),
        "inch": getattr(units, "inch"),
        "Image": getattr(platypus, "Image"),
        "Paragraph": getattr(platypus, "Paragraph"),
        "SimpleDocTemplate": getattr(platypus, "SimpleDocTemplate"),
        "Spacer": getattr(platypus, "Spacer"),
        "Table": getattr(platypus, "Table"),
        "TableStyle": getattr(platypus, "TableStyle"),
    }


def _risk_band(score: float) -> str:
    if score < 0.35:
        return "LOW"
    if score < 0.70:
        return "MEDIUM"
    return "HIGH"


def _fraud_risk_visual(score: float, components: dict[str, Any]) -> Any:
    Drawing = components["Drawing"]
    Rect = components["Rect"]
    String = components["String"]
    colors = components["colors"]

    drawing = Drawing(350, 40)
    base_rect = Rect(0, 15, 300, 10)
    base_rect.fillColor = colors.lightgrey
    base_rect.strokeColor = colors.lightgrey
    drawing.add(base_rect)

    fill_color = colors.green if score < 0.35 else colors.orange if score < 0.70 else colors.red
    score_rect = Rect(0, 15, max(1, 300 * min(max(score, 0.0), 1.0)), 10)
    score_rect.fillColor = fill_color
    score_rect.strokeColor = fill_color
    drawing.add(score_rect)

    drawing.add(String(0, 28, f"Fraud Risk Score: {score:.3f} ({_risk_band(score)})", fontSize=10))
    return drawing


def _shap_chart(top_features: list[dict[str, Any]], components: dict[str, Any]) -> Any:
    Drawing = components["Drawing"]
    Rect = components["Rect"]
    String = components["String"]
    colors = components["colors"]

    drawing = Drawing(450, 130)
    if not top_features:
        drawing.add(String(0, 100, "No SHAP feature data provided", fontSize=10))
        return drawing

    y = 110
    max_abs = max(abs(float(row.get("shap_value", 0.0))) for row in top_features[:5]) or 1.0
    for row in top_features[:5]:
        feature = str(row.get("feature") or row.get("original_group") or "feature")
        value = float(row.get("shap_value", 0.0))
        width = 180 * abs(value) / max_abs
        color = colors.red if value >= 0 else colors.green
        drawing.add(String(0, y + 3, feature[:24], fontSize=9))
        bar = Rect(170, y, width, 9)
        bar.fillColor = color
        bar.strokeColor = color
        drawing.add(bar)
        drawing.add(String(355, y + 1, f"{value:+.3f}", fontSize=8))
        y -= 22
    return drawing


def _claim_summary_table(claim_data: dict[str, Any], components: dict[str, Any]) -> Any:
    Table = components["Table"]
    TableStyle = components["TableStyle"]
    colors = components["colors"]
    inch = components["inch"]

    rows = [["Field", "Value"]]
    for key, value in claim_data.items():
        if any(pii in key.lower() for pii in ["name", "email", "phone", "address", "ssn", "license"]):
            continue
        rows.append([str(key), str(value)])

    table = Table(rows, colWidths=[2.0 * inch, 4.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def generate_pdf_report(
    output_path: str | Path,
    claim_data: dict[str, Any],
    fraud_score: float,
    damage_assessment: dict[str, Any],
    shap_explanations: dict[str, Any],
    narrative_text: str,
    damage_image_paths: list[str] | None = None,
    logo_path: str | None = None,
) -> Path:
    """Generate professional PDF report with optional image embedding."""
    components = _load_reportlab_components()
    colors = components["colors"]
    letter = components["letter"]
    ParagraphStyle = components["ParagraphStyle"]
    getSampleStyleSheet = components["getSampleStyleSheet"]
    inch = components["inch"]
    Image = components["Image"]
    Paragraph = components["Paragraph"]
    SimpleDocTemplate = components["SimpleDocTemplate"]
    Spacer = components["Spacer"]

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    body_style = styles["BodyText"]
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=16, leading=20)
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading2"], fontSize=12, leading=14)

    story = []

    if logo_path and Path(logo_path).exists():
        story.append(Image(logo_path, width=1.2 * inch, height=0.8 * inch))

    story.append(Paragraph("Insurance Fraud Assessment Report", title_style))
    story.append(Paragraph(datetime.now(timezone.utc).strftime("Generated on %Y-%m-%d %H:%M UTC"), body_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Claim Summary", heading_style))
    story.append(_claim_summary_table(claim_data, components=components))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Fraud Risk Score", heading_style))
    story.append(_fraud_risk_visual(fraud_score, components=components))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Damage Assessment", heading_style))
    damage_text = (
        f"Severity: {float(damage_assessment.get('severity_score', 0.0)):.3f}; "
        f"Affected parts: {damage_assessment.get('affected_parts', [])}; "
        f"Damage counts: {damage_assessment.get('count_by_damage_type', {})}."
    )
    story.append(Paragraph(damage_text, body_style))

    for image_path in (damage_image_paths or [])[:3]:
        path = Path(image_path)
        if path.exists():
            story.append(Spacer(1, 6))
            story.append(Image(str(path), width=2.3 * inch, height=1.7 * inch))

    story.append(Spacer(1, 10))

    story.append(Paragraph("SHAP Feature Importance", heading_style))
    top_features = shap_explanations.get("top_contributing_features") or shap_explanations.get("top_features") or []
    story.append(_shap_chart(top_features, components=components))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Narrative Analysis", heading_style))
    story.append(Paragraph(narrative_text.replace("\n", "<br/>"), body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Recommendation and Next Steps", heading_style))
    recs = extract_recommendations(narrative_text)
    if recs:
        for point in recs:
            story.append(Paragraph(f"• {point}", body_style))
    else:
        story.append(Paragraph("Follow manual fraud review workflow for final adjudication.", body_style))

    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Disclaimer: {DISCLAIMER}", body_style))

    document = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    document.build(story)

    return output
