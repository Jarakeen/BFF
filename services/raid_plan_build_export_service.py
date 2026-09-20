from __future__ import annotations

"""Raid Plan scoped Build export helpers.

Raid Plans own the ordered chair selection; canonical BuildService owns build payloads.
This module joins them for sharing without inventing another persistence store.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.build_service import BuildService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class RaidPlanBuildExport:
    roster: BuildRoster
    seats: tuple[tuple[RaidPlanMember, PlayerBuild], ...]
    unresolved_seats: tuple[str, ...] = ()


def _fallback_matches(
    member: RaidPlanMember,
    builds: tuple[PlayerBuild, ...],
) -> tuple[PlayerBuild, ...]:
    wanted_player = _clean(member.gamertag).casefold()
    wanted_character = _clean(member.character_name).casefold()
    wanted_name = _clean(member.selected_build_name).casefold()

    matches = []
    for build in builds:
        if wanted_player and _clean(build.Gamertag).casefold() != wanted_player:
            continue
        if wanted_character and _clean(build.Name).casefold() != wanted_character:
            continue
        if wanted_name and _clean(build.BuildName).casefold() != wanted_name:
            continue
        matches.append(build)
    return tuple(matches)


def raid_plan_build_export(
    plan: RaidPlan,
    build_service: BuildService,
) -> RaidPlanBuildExport:
    """Resolve exact canonical builds for one Raid Plan, preserving seat order."""

    builds = tuple(build_service.load().Members)
    by_id = {
        _clean(getattr(build, "BuildId", "")): build
        for build in builds
        if _clean(getattr(build, "BuildId", ""))
    }

    resolved: list[tuple[RaidPlanMember, PlayerBuild]] = []
    unresolved: list[str] = []
    seen_ids: set[str] = set()

    for member in plan.members:
        selected_id = _clean(member.selected_build_id)
        build = by_id.get(selected_id) if selected_id else None

        if build is None and not selected_id and member.selected_build_name:
            matches = _fallback_matches(member, builds)
            build = matches[0] if len(matches) == 1 else None

        if build is None:
            if member.build_selected or member.planned_gear_sets or member.planned_skills:
                unresolved.append(member.seat_id)
            continue

        build_id = _clean(getattr(build, "BuildId", ""))
        if build_id and build_id in seen_ids:
            continue
        if build_id:
            seen_ids.add(build_id)
        resolved.append((member, build))

    return RaidPlanBuildExport(
        roster=BuildRoster(Members=[build for _, build in resolved]),
        seats=tuple(resolved),
        unresolved_seats=tuple(unresolved),
    )


def _planned_or_saved_sets(member: RaidPlanMember, build: PlayerBuild) -> tuple[str, ...]:
    planned = tuple(_clean(value) for value in member.planned_gear_sets if _clean(value))
    if planned:
        return planned

    values: list[str] = []
    for slot in build.Armor.values():
        if isinstance(slot, dict):
            values.extend((_clean(slot.get("Set")), _clean(slot.get("Set2"))))
    for slot in (
        build.FrontBarWeapon,
        build.FrontBarOffHand,
        build.BackBarWeapon,
        build.BackBarOffHand,
        build.Necklace,
        build.Ring1,
        build.Ring2,
    ):
        values.extend((_clean(getattr(slot, "Set", "")), _clean(getattr(slot, "Set2", ""))))
    return tuple(dict.fromkeys(value for value in values if value))


def raid_plan_discord_builds_text(
    plan: RaidPlan,
    export: RaidPlanBuildExport,
) -> str:
    """Format the Raid Plan's exact resolved builds for Discord clipboard sharing."""

    difficulty = _clean(plan.difficulty) or "Difficulty not set"
    lines = [
        f"**{_clean(plan.name)}**",
        f"{_clean(plan.trial_id)} • {difficulty}",
        "",
        "**Builds**",
    ]

    for member, build in export.seats:
        player = _clean(member.gamertag) or _clean(build.Gamertag) or "Open"
        character = _clean(member.character_name) or _clean(build.Name)
        eso_class = _clean(member.eso_class) or _clean(build.EsoClass)
        build_name = _clean(build.BuildName) or _clean(member.selected_build_name) or "Build"
        identity = " • ".join(value for value in (player, character, eso_class) if value)
        lines.append(f"**{member.seat_id}** | {identity}")
        lines.append(f"↳ {build_name}")

        sets = _planned_or_saved_sets(member, build)
        if sets:
            lines.append("↳ Sets: " + " + ".join(sets))
        skills = tuple(_clean(value) for value in member.planned_skills if _clean(value))
        if skills:
            lines.append("↳ Planned skills: " + ", ".join(skills))

    if export.unresolved_seats:
        lines.extend(
            (
                "",
                "⚠ Unresolved build seats: " + ", ".join(export.unresolved_seats),
            )
        )

    return "\n".join(lines).strip()


def export_raid_plan_builds_csv(
    plan: RaidPlan,
    export: RaidPlanBuildExport,
    path: str | Path,
) -> Path:
    """Write a compact, spreadsheet-friendly Raid Plan build sheet."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "Seat",
                "Player",
                "Character",
                "Class",
                "Role",
                "Build",
                "Sets",
                "Planned Skills",
                "Mundus",
                "Primary Assignment",
                "Utility Assignments",
            )
        )
        for member, build in export.seats:
            writer.writerow(
                (
                    member.seat_id,
                    _clean(member.gamertag) or _clean(build.Gamertag),
                    _clean(member.character_name) or _clean(build.Name),
                    _clean(member.eso_class) or _clean(build.EsoClass),
                    _clean(member.role) or _clean(build.Role),
                    _clean(build.BuildName) or _clean(member.selected_build_name),
                    " + ".join(_planned_or_saved_sets(member, build)),
                    ", ".join(_clean(value) for value in member.planned_skills if _clean(value)),
                    _clean(member.planned_mundus) or _clean(build.Mundus),
                    _clean(member.primary_assignment),
                    ", ".join(_clean(value) for value in member.utility_assignments if _clean(value)),
                )
            )
    return target


def export_raid_plan_builds_pdf(
    plan: RaidPlan,
    export: RaidPlanBuildExport,
    path: str | Path,
) -> Path:
    """Write an intentionally ink-light Raid Plan build sheet.

    The export uses a white page, black/gray text, hairline rules, and no filled
    panels, background art, textures, or decorative blocks.
    """

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError(
            "PDF export requires ReportLab. The packaged FoundryDock build includes it."
        ) from exc

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    black = colors.black
    dark_gray = colors.HexColor("#333333")
    mid_gray = colors.HexColor("#777777")
    light_gray = colors.HexColor("#C8C8C8")

    title_style = ParagraphStyle(
        "InkLightTitle",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=black,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "InkLightSubtitle",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=mid_gray,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "InkLightBody",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=dark_gray,
    )
    head_style = ParagraphStyle(
        "InkLightHead",
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=8.5,
        textColor=black,
    )

    doc = SimpleDocTemplate(
        str(target),
        pagesize=LETTER,
        leftMargin=0.42 * inch,
        rightMargin=0.42 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.42 * inch,
        title=f"{_clean(plan.name)} Raid Plan Builds",
    )
    story = [
        Paragraph(_clean(plan.name) or "Raid Plan", title_style),
        Paragraph(
            f"{_clean(plan.trial_id)} · {_clean(plan.difficulty) or 'Difficulty not set'} · "
            f"{len(export.seats)} resolved build(s)",
            subtitle_style,
        ),
    ]

    rows = [
        [
            Paragraph("Seat", head_style),
            Paragraph("Player / Character", head_style),
            Paragraph("Class", head_style),
            Paragraph("Build", head_style),
            Paragraph("Sets / Skills", head_style),
            Paragraph("Assignment", head_style),
        ]
    ]
    for member, build in export.seats:
        identity = _clean(member.gamertag) or _clean(build.Gamertag) or "Open"
        character = _clean(member.character_name) or _clean(build.Name)
        if character:
            identity = f"{identity}<br/><font size='6'>{character}</font>"

        build_name = _clean(build.BuildName) or _clean(member.selected_build_name) or "Build"
        sets = _planned_or_saved_sets(member, build)
        skills = tuple(_clean(value) for value in member.planned_skills if _clean(value))
        setup_lines = []
        if sets:
            setup_lines.append(" + ".join(sets))
        if skills:
            setup_lines.append("Skills: " + ", ".join(skills))
        if member.planned_mundus:
            setup_lines.append("Mundus: " + _clean(member.planned_mundus))

        assignments = [_clean(member.primary_assignment)]
        assignments.extend(_clean(value) for value in member.utility_assignments)
        assignment_text = "<br/>".join(value for value in assignments if value) or "—"

        rows.append(
            [
                Paragraph(_clean(member.seat_id), body_style),
                Paragraph(identity, body_style),
                Paragraph(_clean(member.eso_class) or _clean(build.EsoClass) or "—", body_style),
                Paragraph(build_name, body_style),
                Paragraph("<br/>".join(setup_lines) or "—", body_style),
                Paragraph(assignment_text, body_style),
            ]
        )

    table = Table(
        rows,
        colWidths=(0.58 * inch, 1.28 * inch, 0.75 * inch, 1.24 * inch, 2.45 * inch, 1.0 * inch),
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, black),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, light_gray),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )
    story.append(table)

    if export.unresolved_seats:
        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                "Unresolved build seats: " + ", ".join(export.unresolved_seats),
                subtitle_style,
            )
        )

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Printer-friendly export · white background · no decorative fills",
            subtitle_style,
        )
    )
    doc.build(story)
    return target


__all__ = [
    "RaidPlanBuildExport",
    "export_raid_plan_builds_csv",
    "export_raid_plan_builds_pdf",
    "raid_plan_build_export",
    "raid_plan_discord_builds_text",
]
