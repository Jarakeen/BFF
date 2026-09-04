from __future__ import annotations

"""Human-readable PDF exports for BFF build and roster sharing.

CSV remains the machine-readable interchange format. This module owns the
presentation layer for documents intended to be handed to another person.
The active BFF visual theme selects either the Field Notes treatment or Rylo's
urban operations treatment without changing the underlying game data.
"""

from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.accessibility_preferences import (
    AccessibilityPreferences,
    VISUAL_THEME_FOUNDRY,
    VISUAL_THEME_RYLO,
)


@dataclass(frozen=True)
class ShareDocumentTheme:
    key: str
    brand: str
    document_label: str
    motto: str
    background: str
    surface: str
    surface_alt: str
    header: str
    text: str
    muted: str
    accent: str
    alert: str
    rule: str
    heading_font: str
    body_font: str


FOUNDRY_SHARE_THEME = ShareDocumentTheme(
    key=VISUAL_THEME_FOUNDRY,
    brand="BLACK FEATHER FOUNDRY",
    document_label="FIELD NOTES",
    motto="Every legend starts as a bad idea.",
    background="#E9D8B8",
    surface="#F2E4C8",
    surface_alt="#E3CEAA",
    header="#0B1719",
    text="#1B1A18",
    muted="#675C4E",
    accent="#C8A46A",
    alert="#8E513F",
    rule="#8A6F45",
    heading_font="Times-Bold",
    body_font="Helvetica",
)

RYLO_SHARE_THEME = ShareDocumentTheme(
    key=VISUAL_THEME_RYLO,
    brand="RYLO",
    document_label="OPERATIONS RECORD",
    motto="CROSS THE DARKNESS.",
    background="#0B0B0E",
    surface="#1A1A1E",
    surface_alt="#121214",
    header="#08080A",
    text="#BEB6A6",
    muted="#858078",
    accent="#8B0E14",
    alert="#C79A3B",
    rule="#2B2B31",
    heading_font="Helvetica-Bold",
    body_font="Helvetica",
)


def resolve_share_theme(theme_name: str | None = None) -> ShareDocumentTheme:
    requested = str(theme_name or AccessibilityPreferences().visual_theme()).strip().casefold()
    return RYLO_SHARE_THEME if requested == VISUAL_THEME_RYLO else FOUNDRY_SHARE_THEME


def _bar_text(skills: Sequence[str]) -> str:
    return "  •  ".join(str(skill).strip() for skill in skills if str(skill).strip()) or "—"


def _gear_value(value, field: str) -> str:
    if hasattr(value, field):
        return str(getattr(value, field, "") or "").strip()
    if isinstance(value, Mapping):
        return str(value.get(field, "") or "").strip()
    return ""


def _paragraph_text(value: object) -> str:
    return escape(str(value or "—")).replace("\n", "<br/>")


class ShareDocumentExporter:
    """Render themed build dossiers and roster operation sheets."""

    def export_builds(
        self,
        roster: BuildRoster,
        path: str | Path,
        *,
        theme_name: str | None = None,
    ) -> Path:
        theme = resolve_share_theme(theme_name)
        self._export_builds_reportlab(roster, Path(path), theme)
        return Path(path)

    def export_roster(
        self,
        members: Iterable[RosterMember],
        path: str | Path,
        *,
        assignments: Sequence[Mapping[str, object]] | None = None,
        title: str = "Raid Roster",
        theme_name: str | None = None,
    ) -> Path:
        theme = resolve_share_theme(theme_name)
        self._export_roster_reportlab(
            list(members),
            Path(path),
            theme,
            assignments=list(assignments or ()),
            title=title,
        )
        return Path(path)

    @staticmethod
    def _reportlab():
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                KeepTogether,
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Pretty PDF export requires ReportLab. The packaged BFF build includes it."
            ) from exc
        return {
            "colors": colors,
            "TA_CENTER": TA_CENTER,
            "TA_LEFT": TA_LEFT,
            "LETTER": LETTER,
            "ParagraphStyle": ParagraphStyle,
            "inch": inch,
            "KeepTogether": KeepTogether,
            "PageBreak": PageBreak,
            "Paragraph": Paragraph,
            "SimpleDocTemplate": SimpleDocTemplate,
            "Spacer": Spacer,
            "Table": Table,
            "TableStyle": TableStyle,
        }

    def _styles(self, rl, theme: ShareDocumentTheme):
        colors = rl["colors"]
        ParagraphStyle = rl["ParagraphStyle"]
        text = colors.HexColor(theme.text)
        muted = colors.HexColor(theme.muted)
        accent = colors.HexColor(theme.accent)
        return {
            "hero": ParagraphStyle(
                "ShareHero",
                fontName=theme.heading_font,
                fontSize=22,
                leading=25,
                textColor=text,
                spaceAfter=2,
            ),
            "subhero": ParagraphStyle(
                "ShareSubhero",
                fontName=theme.heading_font,
                fontSize=11,
                leading=14,
                textColor=accent,
                spaceAfter=7,
            ),
            "section": ParagraphStyle(
                "ShareSection",
                fontName=theme.heading_font,
                fontSize=10,
                leading=12,
                textColor=accent,
                spaceBefore=4,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "ShareBody",
                fontName=theme.body_font,
                fontSize=8.2,
                leading=10.5,
                textColor=text,
            ),
            "small": ParagraphStyle(
                "ShareSmall",
                fontName=theme.body_font,
                fontSize=7.2,
                leading=9,
                textColor=muted,
            ),
            "center": ParagraphStyle(
                "ShareCenter",
                fontName=theme.body_font,
                fontSize=8,
                leading=10,
                alignment=rl["TA_CENTER"],
                textColor=text,
            ),
        }

    def _page_decorator(self, rl, theme: ShareDocumentTheme, document_kind: str):
        colors = rl["colors"]
        inch = rl["inch"]

        def draw(canvas, doc):
            width, height = doc.pagesize
            canvas.saveState()
            canvas.setFillColor(colors.HexColor(theme.background))
            canvas.rect(0, 0, width, height, stroke=0, fill=1)

            canvas.setFillColor(colors.HexColor(theme.header))
            canvas.rect(0, height - 0.72 * inch, width, 0.72 * inch, stroke=0, fill=1)
            canvas.setStrokeColor(colors.HexColor(theme.accent))
            canvas.setLineWidth(1.0 if theme.key == VISUAL_THEME_FOUNDRY else 1.5)
            canvas.line(0.42 * inch, height - 0.72 * inch, width - 0.42 * inch, height - 0.72 * inch)

            canvas.setFillColor(colors.HexColor(theme.text if theme.key == VISUAL_THEME_RYLO else theme.accent))
            canvas.setFont(theme.heading_font, 14)
            canvas.drawString(0.48 * inch, height - 0.40 * inch, theme.brand)
            canvas.setFont(theme.body_font, 7)
            canvas.setFillColor(colors.HexColor(theme.muted if theme.key == VISUAL_THEME_RYLO else "#D8C59E"))
            canvas.drawRightString(width - 0.48 * inch, height - 0.39 * inch, f"{theme.document_label}  ·  {document_kind.upper()}")

            canvas.setStrokeColor(colors.HexColor(theme.rule))
            canvas.setLineWidth(0.65)
            canvas.line(0.48 * inch, 0.42 * inch, width - 0.48 * inch, 0.42 * inch)
            canvas.setFont(theme.body_font, 6.8)
            canvas.setFillColor(colors.HexColor(theme.muted))
            canvas.drawString(0.48 * inch, 0.24 * inch, theme.motto)
            stamp = datetime.now().strftime("Generated %b %d, %Y")
            canvas.drawRightString(width - 0.48 * inch, 0.24 * inch, f"{stamp}  ·  Page {doc.page}")

            # Rylo gets the simple red operations mark; Foundry gets a quiet gold corner tick.
            canvas.setStrokeColor(colors.HexColor(theme.accent))
            if theme.key == VISUAL_THEME_RYLO:
                canvas.setLineWidth(2)
                canvas.line(0.48 * inch, height - 0.13 * inch, 1.20 * inch, height - 0.13 * inch)
            else:
                canvas.setLineWidth(0.8)
                canvas.line(width - 0.72 * inch, 0.55 * inch, width - 0.48 * inch, 0.55 * inch)
                canvas.line(width - 0.48 * inch, 0.55 * inch, width - 0.48 * inch, 0.79 * inch)
            canvas.restoreState()

        return draw

    def _card_table(self, rl, theme: ShareDocumentTheme, data, widths, *, header=True, font_size=7.5):
        colors = rl["colors"]
        Table = rl["Table"]
        TableStyle = rl["TableStyle"]
        table = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
        commands = [
            ("BOX", (0, 0), (-1, -1), 0.65, colors.HexColor(theme.rule)),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor(theme.rule)),
            ("FONTNAME", (0, 0), (-1, -1), theme.body_font),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEADING", (0, 0), (-1, -1), font_size + 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(theme.text)),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(theme.surface)),
        ]
        if header:
            commands.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme.header)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(theme.accent if theme.key == VISUAL_THEME_FOUNDRY else theme.text)),
                ("FONTNAME", (0, 0), (-1, 0), theme.heading_font),
            ])
        table.setStyle(TableStyle(commands))
        return table

    def _export_builds_reportlab(self, roster: BuildRoster, path: Path, theme: ShareDocumentTheme) -> None:
        rl = self._reportlab()
        inch = rl["inch"]
        styles = self._styles(rl, theme)
        Paragraph = rl["Paragraph"]
        Spacer = rl["Spacer"]
        PageBreak = rl["PageBreak"]
        SimpleDocTemplate = rl["SimpleDocTemplate"]
        KeepTogether = rl["KeepTogether"]

        path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=rl["LETTER"],
            leftMargin=0.48 * inch,
            rightMargin=0.48 * inch,
            topMargin=0.92 * inch,
            bottomMargin=0.58 * inch,
            title=f"{theme.brand} Build Export",
        )
        story = []
        members = [member for member in roster.Members if member.Name or member.Gamertag or member.BuildName]

        for index, member in enumerate(members):
            identity = member.Name or member.Gamertag or "Unnamed Character"
            build_name = member.BuildName or "Current Build"
            role = member.Role or "Unspecified Role"
            story.append(Paragraph(_paragraph_text(identity).upper(), styles["hero"]))
            story.append(Paragraph(_paragraph_text(build_name).upper(), styles["subhero"]))

            meta = [
                ["CLASS", _paragraph_text(member.EsoClass), "RACE", _paragraph_text(member.Race)],
                ["ROLE", _paragraph_text(role), "MUNDUS", _paragraph_text(member.Mundus)],
                ["ATTRIBUTES", f"H {member.AttributeHealth}  ·  M {member.AttributeMagicka}  ·  S {member.AttributeStamina}", "PLAYER", _paragraph_text(member.Gamertag)],
            ]
            story.append(self._card_table(rl, theme, meta, [0.78 * inch, 2.20 * inch, 0.78 * inch, 2.75 * inch], header=False))
            story.append(Spacer(1, 8))

            story.append(Paragraph("GEAR", styles["section"]))
            gear_rows = [["SLOT", "SET", "TRAIT", "ENCHANT"]]
            for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
                value = member.Armor.get(slot, {})
                gear_rows.append([
                    slot,
                    _paragraph_text(_gear_value(value, "Set")),
                    _paragraph_text(_gear_value(value, "Trait")),
                    _paragraph_text(_gear_value(value, "Enchant")),
                ])
            for label, value in (
                ("Front Weapon", member.FrontBarWeapon),
                ("Front Off Hand", member.FrontBarOffHand),
                ("Back Weapon", member.BackBarWeapon),
                ("Back Off Hand", member.BackBarOffHand),
                ("Necklace", member.Necklace),
                ("Ring 1", member.Ring1),
                ("Ring 2", member.Ring2),
            ):
                if not any((_gear_value(value, "Set"), _gear_value(value, "Trait"), _gear_value(value, "Enchant"), _gear_value(value, "WeaponType"))):
                    continue
                set_text = _gear_value(value, "Set")
                weapon_type = _gear_value(value, "WeaponType")
                if weapon_type:
                    set_text = f"{set_text} · {weapon_type}" if set_text else weapon_type
                gear_rows.append([
                    label,
                    _paragraph_text(set_text),
                    _paragraph_text(_gear_value(value, "Trait")),
                    _paragraph_text(_gear_value(value, "Enchant")),
                ])
            story.append(self._card_table(rl, theme, gear_rows, [1.08 * inch, 2.52 * inch, 1.15 * inch, 1.75 * inch]))
            story.append(Spacer(1, 8))

            story.append(Paragraph("SKILLS & CONSUMABLES", styles["section"]))
            bars = [
                ["FRONT BAR", Paragraph(_paragraph_text(_bar_text(member.FrontBarSkills)), styles["body"])],
                ["BACK BAR", Paragraph(_paragraph_text(_bar_text(member.BackBarSkills)), styles["body"])],
                ["FOOD", Paragraph(_paragraph_text(member.Food), styles["body"])],
                ["POTION", Paragraph(_paragraph_text(member.Potion), styles["body"])],
            ]
            story.append(self._card_table(rl, theme, bars, [1.05 * inch, 5.45 * inch], header=False))

            cp_text = "; ".join(
                f"{cp.Name} ({cp.Points})" if cp.Points else cp.Name
                for cp in member.ChampionPoints
                if cp.Name
            ) or "—"
            story.append(Spacer(1, 7))
            story.append(KeepTogether([
                Paragraph("CHAMPION POINTS", styles["section"]),
                self._card_table(
                    rl,
                    theme,
                    [[Paragraph(_paragraph_text(cp_text), styles["body"]) ]],
                    [6.50 * inch],
                    header=False,
                ),
            ]))

            if member.BossLoadouts:
                alternate_rows = [["ENCOUNTER", "FRONT / BACK CHANGES", "CONSUMABLES / NOTES"]]
                for boss in member.BossLoadouts:
                    if not boss.BossName:
                        continue
                    bar_change = f"F: {_bar_text(boss.FrontBarSkills)}<br/>B: {_bar_text(boss.BackBarSkills)}"
                    detail = "<br/>".join(
                        part for part in (
                            f"Food: {_paragraph_text(boss.Food)}" if boss.Food else "",
                            f"Potion: {_paragraph_text(boss.Potion)}" if boss.Potion else "",
                            _paragraph_text(boss.Notes) if boss.Notes else "",
                        ) if part
                    ) or "—"
                    alternate_rows.append([
                        Paragraph(_paragraph_text(boss.BossName), styles["body"]),
                        Paragraph(bar_change, styles["small"]),
                        Paragraph(detail, styles["small"]),
                    ])
                if len(alternate_rows) > 1:
                    story.append(Spacer(1, 7))
                    story.append(Paragraph("ENCOUNTER VARIANTS", styles["section"]))
                    story.append(self._card_table(rl, theme, alternate_rows, [1.40 * inch, 2.90 * inch, 2.20 * inch], font_size=7))

            if member.Notes:
                story.append(Spacer(1, 7))
                story.append(Paragraph("NOTES", styles["section"]))
                story.append(self._card_table(
                    rl,
                    theme,
                    [[Paragraph(_paragraph_text(member.Notes), styles["body"]) ]],
                    [6.50 * inch],
                    header=False,
                ))

            if index < len(members) - 1:
                story.append(PageBreak())

        if not story:
            story.append(Paragraph("No saved builds to export.", styles["body"]))

        decorator = self._page_decorator(rl, theme, "Build Dossier" if theme.key == VISUAL_THEME_FOUNDRY else "Build Record")
        doc.build(story, onFirstPage=decorator, onLaterPages=decorator)

    def _export_roster_reportlab(
        self,
        members: list[RosterMember],
        path: Path,
        theme: ShareDocumentTheme,
        *,
        assignments: list[Mapping[str, object]],
        title: str,
    ) -> None:
        rl = self._reportlab()
        inch = rl["inch"]
        styles = self._styles(rl, theme)
        Paragraph = rl["Paragraph"]
        Spacer = rl["Spacer"]
        SimpleDocTemplate = rl["SimpleDocTemplate"]

        path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=rl["LETTER"],
            leftMargin=0.48 * inch,
            rightMargin=0.48 * inch,
            topMargin=0.92 * inch,
            bottomMargin=0.58 * inch,
            title=f"{theme.brand} Roster Export",
        )
        story = [
            Paragraph(_paragraph_text(title).upper(), styles["hero"]),
            Paragraph("RAID ROSTER" if theme.key == VISUAL_THEME_FOUNDRY else "RAID OPERATIONS", styles["subhero"]),
        ]

        total = len(members)
        active = sum(1 for member in members if str(member.Status).casefold() == "active")
        tanks = sum(1 for member in members if "tank" in str(member.PrimaryRole).casefold())
        healers = sum(1 for member in members if "heal" in str(member.PrimaryRole).casefold())
        damage = max(0, total - tanks - healers)
        summary = [
            ["TOTAL", str(total), "ACTIVE", f"{active}/{total or 0}"],
            ["TANKS", str(tanks), "HEALERS", str(healers)],
            ["DAMAGE", str(damage), "STATUS", "READY" if total and active == total else "CHECK ROSTER"],
        ]
        story.append(self._card_table(rl, theme, summary, [0.80 * inch, 1.25 * inch, 0.85 * inch, 3.60 * inch], header=False))
        story.append(Spacer(1, 9))

        if assignments:
            story.append(Paragraph("ASSIGNMENTS", styles["section"]))
            headers = ["PLAYER", "ROLE", "CLASS", "BUILD", "PRIMARY", "SECONDARY", "READY"]
            rows = [headers]
            for item in assignments:
                rows.append([
                    Paragraph(_paragraph_text(item.get("player")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("role")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("class")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("build")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("primary")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("secondary")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("ready")), styles["center"]),
                ])
            story.append(self._card_table(
                rl,
                theme,
                rows,
                [0.90 * inch, 0.65 * inch, 0.72 * inch, 0.80 * inch, 1.27 * inch, 1.35 * inch, 0.55 * inch],
                font_size=6.5,
            ))
            story.append(Spacer(1, 9))

        story.append(Paragraph("PERSONNEL", styles["section"]))
        personnel = [["PLAYER", "CHARACTER", "CLASS", "PRIMARY ROLE", "SECONDARY ROLE", "TEAM", "STATUS"]]
        for member in members:
            personnel.append([
                Paragraph(_paragraph_text(member.PlayerName), styles["small"]),
                Paragraph(_paragraph_text(member.CharacterName), styles["small"]),
                Paragraph(_paragraph_text(member.EsoClass), styles["small"]),
                Paragraph(_paragraph_text(member.PrimaryRole), styles["small"]),
                Paragraph(_paragraph_text(member.SecondaryRole), styles["small"]),
                Paragraph(_paragraph_text(member.Team), styles["small"]),
                Paragraph(_paragraph_text(member.Status), styles["small"]),
            ])
        story.append(self._card_table(
            rl,
            theme,
            personnel,
            [0.95 * inch, 1.00 * inch, 0.72 * inch, 0.95 * inch, 1.05 * inch, 0.90 * inch, 0.70 * inch],
            font_size=6.5,
        ))

        decorator = self._page_decorator(rl, theme, "Roster Sheet" if theme.key == VISUAL_THEME_FOUNDRY else "Operations Roster")
        doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
