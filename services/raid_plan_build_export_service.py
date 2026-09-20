from __future__ import annotations

"""Raid Plan scoped Build export helpers.

Raid Plans own the ordered chair selection; canonical BuildService owns build payloads.
This module joins them for sharing without inventing another persistence store.
"""

from dataclasses import dataclass

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


__all__ = [
    "RaidPlanBuildExport",
    "raid_plan_build_export",
    "raid_plan_discord_builds_text",
]
