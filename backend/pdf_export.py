"""PDF Strategy Brief generation using ReportLab.

Spec requirement: PDF must contain every citation referenced in the on-screen
output. We render in three sections — inputs echo, comparison table sorted by
after-tax wealth to recipient, and an exhaustive citations appendix.
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from engine.engine import CompareResult
from engine.inputs import DonorInputs


def _money(amount) -> str:
    try:
        return f"${Decimal(str(amount)):,.0f}"
    except Exception:  # noqa: BLE001
        return str(amount)


def _percent(amount) -> str:
    try:
        return f"{Decimal(str(amount)) * 100:.1f}%"
    except Exception:  # noqa: BLE001
        return str(amount)


def build_strategy_brief_pdf(
    inputs: DonorInputs,
    result: CompareResult,
    rules: dict,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Wealth Transfer Strategy Brief",
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=body, fontSize=8, leading=10, textColor=colors.grey)
    italic = ParagraphStyle("Italic", parent=body, fontSize=9, leading=11, fontName="Helvetica-Oblique")

    story: list = []

    # ----- Header -----
    story.append(Paragraph("Wealth Transfer Strategy Brief", h1))
    story.append(Paragraph(
        f"Prepared {date.today().isoformat()} &middot; Tax Year {rules['tax_year']} &middot; "
        f"Rules version: {rules['last_updated']}",
        small,
    ))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "<b>Educational model, not tax or legal advice.</b> Confirm with a qualified "
        "advisor before acting. All numeric outputs trace to the U.S. Internal Revenue "
        "Code, Treasury regulations, and state statutes cited in the appendix.",
        italic,
    ))
    story.append(Spacer(1, 0.2 * inch))

    # ----- Inputs echo -----
    story.append(Paragraph("Inputs", h2))
    input_rows = [
        ["Donor age", str(inputs.donor_age)],
        ["Donor AGI", _money(inputs.donor_gross_income_agi)],
        ["Filing status", inputs.filing_status.value.upper()],
        ["State of domicile", inputs.state.value],
        ["Donor net worth", _money(inputs.donor_net_worth)],
        ["Spouse present", "Yes" if inputs.spouse_present else "No"],
        ["Child age", str(inputs.child_age)],
        ["Child earned income", _money(inputs.child_earned_income)],
        ["Investment horizon", f"{inputs.investment_horizon_years} years"],
        ["Annual contribution", _money(inputs.annual_contribution)],
        ["Expected pre-tax return", _percent(inputs.expected_pretax_return)],
        ["Inflation assumption", _percent(inputs.inflation_rate)],
        ["Mortality model", inputs.mortality_model.value],
        ["5-year 529 election", "Yes" if inputs.elect_529_five_year else "No"],
        ["Gift-splitting elected", "Yes" if inputs.elect_gift_splitting else "No"],
    ]
    tbl = Table(input_rows, colWidths=[2.2 * inch, 3.2 * inch])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.25 * inch))

    # ----- Comparison table -----
    story.append(Paragraph("Strategy Comparison (sorted by after-tax wealth to recipient)", h2))

    available = [r for r in result.results if r.is_available]
    blocked = [r for r in result.results if not r.is_available]
    sorted_results = sorted(available, key=lambda r: Decimal(str(r.after_tax_wealth_to_recipient)), reverse=True)

    header_row = ["Strategy", "Pretax Terminal", "Total Tax", "After-Tax to Heir", "ETR"]
    rows = [header_row]
    for r in sorted_results:
        total_tax = sum(Decimal(str(v)) for v in r.taxes_paid_breakdown.values())
        rows.append([
            r.strategy_name,
            _money(r.pretax_terminal_value),
            _money(total_tax),
            _money(r.after_tax_wealth_to_recipient),
            _percent(r.effective_tax_rate),
        ])
    cmp_tbl = Table(rows, colWidths=[1.6 * inch, 1.2 * inch, 1.1 * inch, 1.4 * inch, 0.8 * inch])
    cmp_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    story.append(cmp_tbl)
    story.append(Spacer(1, 0.2 * inch))

    if blocked:
        story.append(Paragraph("Unavailable strategies", h2))
        for r in blocked:
            story.append(Paragraph(f"<b>{r.strategy_name}.</b> {r.unavailable_reason}", body))

    # ----- Warnings & recommendations -----
    if result.recommendations:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("Recommendations", h2))
        for rec in result.recommendations:
            # Surface category and priority as a small leading tag — same
            # information density as the dashboard cards.
            tag = f"[{rec.category}]"
            if rec.priority == "high":
                tag = f"<b>{tag}</b>"
            story.append(Paragraph(f"&bull; {tag} {rec.message}", body))

    warnings_consolidated = []
    for r in result.results:
        for w in r.warnings:
            warnings_consolidated.append(f"<b>[{r.strategy_name}]</b> {w}")
    if warnings_consolidated:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("Warnings", h2))
        for w in warnings_consolidated:
            story.append(Paragraph(f"&bull; {w}", body))

    # ----- Per-strategy detail + assumptions -----
    story.append(PageBreak())
    story.append(Paragraph("Strategy detail and assumptions", h1))
    for r in sorted_results + blocked:
        story.append(Paragraph(r.strategy_name, h2))
        if not r.is_available:
            story.append(Paragraph(r.unavailable_reason or "", body))
            continue
        story.append(Paragraph(
            f"Pretax terminal: <b>{_money(r.pretax_terminal_value)}</b> &middot; "
            f"After-tax to heir: <b>{_money(r.after_tax_wealth_to_recipient)}</b> &middot; "
            f"ETR: <b>{_percent(r.effective_tax_rate)}</b>",
            body,
        ))
        breakdown_rows = [["Tax line", "Amount"]] + [
            [k.replace("_", " ").title(), _money(v)] for k, v in r.taxes_paid_breakdown.items()
        ]
        bt = Table(breakdown_rows, colWidths=[2.0 * inch, 1.5 * inch])
        bt.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(bt)
        story.append(Spacer(1, 0.08 * inch))
        if r.assumptions:
            story.append(Paragraph("<b>Assumptions:</b>", body))
            for a in r.assumptions:
                story.append(Paragraph(f"&bull; {a}", small))
        story.append(Spacer(1, 0.15 * inch))

    # ----- Citations appendix -----
    story.append(PageBreak())
    story.append(Paragraph("Citations", h1))
    seen: set[tuple[str, str]] = set()
    for r in result.results:
        for c in r.citations:
            key = (c.section, c.description)
            if key in seen:
                continue
            seen.add(key)
            story.append(Paragraph(
                f"<b>{c.section}</b> &mdash; {c.description}"
                + (f"<br/><font color='grey' size='7'>{c.url}</font>" if c.url else ""),
                small,
            ))

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        f"Source: {rules['source']}. Rules last updated {rules['last_updated']}.",
        italic,
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
