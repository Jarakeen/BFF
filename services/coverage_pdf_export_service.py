from __future__ import annotations

"""Printer-friendly Coverage export for one saved Raid Plan."""

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from models.raid_plan import RaidPlan


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class CoveragePDFRow:
    effect: str
    provider: str
    backup: str
    source: str
    status: str

    def __post_init__(self) -> None:
        effect = _clean(self.effect)
        if not effect:
            raise ValueError("Coverage PDF row requires an effect")
        object.__setattr__(self, "effect", effect)
        object.__setattr__(self, "provider", _clean(self.provider) or "—")
        object.__setattr__(self, "backup", _clean(self.backup) or "—")
        object.__setattr__(self, "source", _clean(self.source) or "—")
        object.__setattr__(self, "status", _clean(self.status) or "Covered")


def export_coverage_pdf(
    plan: RaidPlan,
    rows: tuple[CoveragePDFRow, ...],
    path: str | Path,
) -> Path:
    """Write a low-ink FoundryDock Coverage field sheet."""
    if not isinstance(plan, RaidPlan):
        raise TypeError("Coverage PDF export requires a RaidPlan")
    if any(not isinstance(row, CoveragePDFRow) for row in rows):
        raise TypeError("Coverage PDF export rows must be CoveragePDFRow records")

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, LETTER
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError(
            "Coverage PDF export requires ReportLab. The packaged FoundryDock build includes it."
        ) from exc

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    teal = colors.HexColor("#1F3F45")
    gold = colors.HexColor("#C8A46A")
    dark = colors.HexColor("#303A3C")
    gray = colors.HexColor("#687476")
    pale = colors.HexColor("#E5ECEB")
    mist = colors.HexColor("#F3F7F6")
    parchment = colors.HexColor("#FBF8F0")
    hair = colors.HexColor("#D9DFDE")

    title_style = ParagraphStyle(
        "CoverageTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=teal,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "CoverageSubtitle",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=gray,
        spaceAfter=8,
    )
    header_style = ParagraphStyle(
        "CoverageHeader",
        fontName="Helvetica-Bold",
        fontSize=7.4,
        leading=9,
        textColor=teal,
    )
    body_style = ParagraphStyle(
        "CoverageBody",
        fontName="Helvetica",
        fontSize=7.4,
        leading=9.2,
        textColor=dark,
    )

    def paragraph(value: object, style=body_style) -> Paragraph:
        return Paragraph(escape(_clean(value) or "—"), style)

    def decorate_page(canvas, document) -> None:
        canvas.saveState()
        width, height = landscape(LETTER)
        canvas.setFillColor(teal)
        canvas.rect(0, height - 0.16 * inch, width, 0.16 * inch, fill=1, stroke=0)
        canvas.setFillColor(gold)
        canvas.rect(0, height - 0.20 * inch, width, 0.035 * inch, fill=1, stroke=0)
        canvas.setFont("Helvetica", 6.8)
        canvas.setFillColor(gray)
        canvas.drawString(0.45 * inch, 0.23 * inch, "FoundryDock • Leave Better Records")
        canvas.drawRightString(width - 0.45 * inch, 0.23 * inch, f"Page {document.page}")
        canvas.restoreState()

    difficulty = _clean(plan.difficulty) or "Difficulty not set"
    trial = _clean(plan.trial_id).replace("-", " ").title() or "Trial not set"
    team = _clean(plan.team_name) or "No Team"
    plan_name = _clean(plan.name) or "Raid Plan"

    doc = SimpleDocTemplate(
        str(target),
        pagesize=landscape(LETTER),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.43 * inch,
        bottomMargin=0.42 * inch,
        title=f"{plan_name} Coverage",
        author="FoundryDock",
    )

    story = [
        Paragraph(escape(plan_name), title_style),
        Paragraph(
            f"{escape(trial)} · {escape(difficulty)} · {escape(team)}"
            f"<br/><b>{len(rows)} covered effects</b> · Raid Plan Coverage field sheet",
            subtitle_style,
        ),
        Spacer(1, 2),
    ]

    table_rows = [[
        paragraph("Effect", header_style),
        paragraph("Provider", header_style),
        paragraph("Backup", header_style),
        paragraph("What Provides It", header_style),
        paragraph("Coverage Status", header_style),
    ]]
    for row in rows:
        table_rows.append([
            paragraph(row.effect),
            paragraph(row.provider),
            paragraph(row.backup),
            paragraph(row.source),
            paragraph(row.status),
        ])

    table = Table(
        table_rows,
        colWidths=(1.55 * inch, 1.55 * inch, 1.35 * inch, 3.35 * inch, 2.0 * inch),
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("BACKGROUND", (0, 0), (-1, 0), parchment),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, gold),
        ("LINEBELOW", (0, 1), (-1, -1), 0.2, hair),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, mist]),
    ]))
    story.append(table)

    if not rows:
        story.append(Spacer(1, 8))
        story.append(Paragraph("No covered effects were available to export.", subtitle_style))

    doc.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    return target


__all__ = ["CoveragePDFRow", "export_coverage_pdf"]
