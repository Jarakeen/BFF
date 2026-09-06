from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Sequence

from models.roster_model import RosterMember
from models.team_schedule import TeamSchedule
from services.accessibility_preferences import VISUAL_THEME_FOUNDRY
from services.share_document_export import ShareDocumentExporter, _paragraph_text, resolve_share_theme


def _public_assignment_build(item: Mapping[str, object]) -> str:
    """Return a recruit-safe build label for the human-facing roster PDF.

    ESO Logs player names are evidence provenance, not recruit identities. Generated
    ESO Logs candidate labels use bullet-delimited segments ending in the observed
    player's name, so remove only that final identity segment for recruit rows.
    """

    build = str(item.get("build") or "").strip()
    player = str(item.get("player") or "").strip()
    if player.casefold() != "recruitment needed" or " • " not in build:
        return build
    parts = [part.strip() for part in build.split(" • ") if part.strip()]
    return " • ".join(parts[:-1]) if len(parts) >= 3 else build


class TeamScheduleShareDocumentExporter(ShareDocumentExporter):
    """Roster share sheets with an obvious, compact team schedule band."""

    def export_roster(
        self,
        members: Iterable[RosterMember],
        path: str | Path,
        *,
        assignments: Sequence[Mapping[str, object]] | None = None,
        title: str = "Raid Roster",
        theme_name: str | None = None,
        team_schedules: Sequence[TeamSchedule] | None = None,
    ) -> Path:
        theme = resolve_share_theme(theme_name)
        self._export_roster_reportlab_with_schedule(
            list(members),
            Path(path),
            theme,
            assignments=list(assignments or ()),
            title=title,
            team_schedules=list(team_schedules or ()),
        )
        return Path(path)

    def _export_roster_reportlab_with_schedule(
        self,
        members: list[RosterMember],
        path: Path,
        theme,
        *,
        assignments: list[Mapping[str, object]],
        title: str,
        team_schedules: list[TeamSchedule],
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
            Paragraph(
                "RAID ROSTER" if theme.key == VISUAL_THEME_FOUNDRY else "RAID OPERATIONS",
                styles["subhero"],
            ),
        ]

        configured = [schedule for schedule in team_schedules if schedule.is_configured]
        if configured:
            story.append(Paragraph("RAID SCHEDULE", styles["section"]))
            schedule_rows = [["TEAM", "DAYS", "START", "TIME ZONE"]]
            for schedule in configured:
                schedule_rows.append([
                    Paragraph(_paragraph_text(schedule.TeamName), styles["body"]),
                    Paragraph(_paragraph_text(schedule.RaidDays), styles["body"]),
                    Paragraph(_paragraph_text(schedule.RaidTime), styles["body"]),
                    Paragraph(_paragraph_text(schedule.TimeZone), styles["body"]),
                ])
            story.append(self._card_table(
                rl,
                theme,
                schedule_rows,
                [1.35 * inch, 1.55 * inch, 1.15 * inch, 2.45 * inch],
                font_size=7.6,
            ))
            story.append(Spacer(1, 9))

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
        story.append(self._card_table(
            rl,
            theme,
            summary,
            [0.80 * inch, 1.25 * inch, 0.85 * inch, 3.60 * inch],
            header=False,
        ))
        story.append(Spacer(1, 9))

        if assignments:
            story.append(Paragraph("ASSIGNMENTS", styles["section"]))
            rows = [["PLAYER", "CLASS", "ROLE", "BUILD"]]
            for item in assignments:
                rows.append([
                    Paragraph(_paragraph_text(item.get("player")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("class")), styles["small"]),
                    Paragraph(_paragraph_text(item.get("role")), styles["small"]),
                    Paragraph(_paragraph_text(_public_assignment_build(item)), styles["small"]),
                ])
            story.append(self._card_table(
                rl,
                theme,
                rows,
                [1.20 * inch, 1.15 * inch, 0.95 * inch, 3.45 * inch],
                font_size=7.2,
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

        decorator = self._page_decorator(
            rl,
            theme,
            "Roster Sheet" if theme.key == VISUAL_THEME_FOUNDRY else "Operations Roster",
        )
        doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
