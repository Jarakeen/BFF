from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.resource_costs import ResourceType
from services.build_service import BuildService
from services.rotation_lokkestiiz_healer_scenario import (
    build_magrat_df_healer_lokkestiiz_scenario,
)


def _semantic_id(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _display_name(semantic_id: str) -> str:
    return " ".join(part.capitalize() for part in semantic_id.split("_") if part)


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _build_name(build) -> str:
    return str(getattr(build, "BuildName", "") or "").strip()


def _find_build(roster, *, character_name: str, build_name: str):
    matches = [
        build
        for build in roster.Members
        if _character_name(build).casefold() == character_name.casefold()
        and _build_name(build).casefold() == build_name.casefold()
    ]
    if not matches:
        raise ValueError(f"saved build not found: {character_name} -> {build_name}")
    if len(matches) > 1:
        raise ValueError(f"saved build is ambiguous: {character_name} -> {build_name}")
    return matches[0]


def _slotted_skill_map(build) -> dict[str, tuple[str, int, str]]:
    result: dict[str, tuple[str, int, str]] = {}
    for bar, values in (
        ("front", getattr(build, "FrontBarSkills", ()) or ()),
        ("back", getattr(build, "BackBarSkills", ()) or ()),
    ):
        for slot, raw_name in enumerate(tuple(values), start=1):
            name = str(raw_name or "").strip()
            if not name:
                continue
            semantic_id = _semantic_id(name)
            if semantic_id in result:
                previous = result[semantic_id]
                raise ValueError(
                    f"semantic skill {semantic_id!r} is ambiguous across saved slots: "
                    f"{previous[0]} {previous[1]} and {bar} {slot}"
                )
            result[semantic_id] = (bar, slot, name)
    return result


def _apply_boss_replacements(
    slotted: dict[str, tuple[str, int, str]],
    replacements,
) -> tuple[dict[str, tuple[str, int, str]], tuple[str, ...]]:
    effective = dict(slotted)
    notes: list[str] = []
    for replacement in replacements:
        outgoing = effective.get(replacement.outgoing_semantic_id)
        if outgoing is None:
            raise ValueError(
                "boss loadout replacement source is not slotted: "
                f"{replacement.outgoing_semantic_id}"
            )
        bar, slot, _display = outgoing
        if bar != replacement.bar:
            raise ValueError(
                "boss loadout replacement source is on the wrong bar: "
                f"{replacement.outgoing_semantic_id} expected {replacement.bar}, got {bar}"
            )
        if replacement.incoming_semantic_id in effective:
            raise ValueError(
                "boss loadout replacement target is already slotted: "
                f"{replacement.incoming_semantic_id}"
            )
        del effective[replacement.outgoing_semantic_id]
        effective[replacement.incoming_semantic_id] = (
            bar,
            slot,
            _display_name(replacement.incoming_semantic_id),
        )
        notes.append(
            f"{bar} slot {slot}: {replacement.outgoing_semantic_id} -> "
            f"{replacement.incoming_semantic_id}"
        )
    return effective, tuple(notes)


def _ultimate_cost_lines(*, database_path: Path, semantic_id: str) -> tuple[str, ...]:
    display_name = _display_name(semantic_id)
    resolution = AbilityCostRepository(database_path).resolve_name(display_name)
    lines = [f"SELECTED_ULTIMATE: {semantic_id} -> {display_name}"]
    cost = resolution.base_cost
    if cost is None:
        detail = "; ".join(resolution.unresolved) or "canonical cost is unresolved"
        lines.append(f"ULTIMATE_COST: UNRESOLVED: {detail}")
        return tuple(lines)
    if ResourceType.ULTIMATE not in cost.resources:
        resources = ", ".join(resource.value for resource in cost.resources)
        lines.append(
            "ULTIMATE_COST: UNRESOLVED: canonical action cost does not consume "
            f"Ultimate (resources={resources})"
        )
        return tuple(lines)
    lines.append(
        f"ULTIMATE_COST: {cost.amount:g} ultimate "
        f"(ability_id={cost.ability_id}, rank={cost.rank}, morph={cost.morph})"
    )
    return tuple(lines)


def audit(*, builds_path: Path, database_path: Path | None = None) -> tuple[str, ...]:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()
    profile = scenario.execution
    roster = BuildService(builds_path).load()
    build = _find_build(
        roster,
        character_name=profile.character_name,
        build_name=profile.build_name,
    )
    base_slotted = _slotted_skill_map(build)
    slotted, replacement_notes = _apply_boss_replacements(
        base_slotted,
        scenario.skill_replacements,
    )

    lines: list[str] = []
    lines.append("PHASE 13 LOKKESTIIZ HEALER EXECUTION AUDIT")
    lines.append(f"BUILD: {profile.character_name} -> {profile.build_name}")
    lines.append(f"ENCOUNTER: {profile.encounter_id}")
    lines.append(f"REQUESTED_CYCLES: {profile.requested_cycles}")
    lines.append(
        "CANONICAL_FLIGHT_TRIGGERS: "
        + ", ".join(f"{value}%" for value in profile.canonical_flight_health_thresholds)
    )
    for note in replacement_notes:
        lines.append(f"BOSS LOADOUT SWAP: {note}")

    missing: list[str] = []
    for semantic_id in profile.required_skill_ids:
        slot = slotted.get(semantic_id)
        if slot is None:
            missing.append(semantic_id)
            lines.append(f"SKILL MISSING: {semantic_id}")
            continue
        bar, slot_number, display_name = slot
        lines.append(
            f"SKILL OK: {semantic_id} -> {bar} slot {slot_number} -> {display_name}"
        )

    ultimates: list[str] = []
    for bar, values in (
        ("front", getattr(build, "FrontBarSkills", ()) or ()),
        ("back", getattr(build, "BackBarSkills", ()) or ()),
    ):
        skills = tuple(values)
        if len(skills) < 6:
            continue
        name = str(skills[5] or "").strip()
        if name:
            ultimates.append(f"{bar} -> {name}")
    lines.append("AVAILABLE_ULTIMATES: " + ("; ".join(ultimates) if ultimates else "none"))

    selected_display = _display_name(scenario.selected_ultimate_semantic_id)
    selected_available = any(
        _semantic_id(item.split(" -> ", 1)[-1]) == scenario.selected_ultimate_semantic_id
        for item in ultimates
    )
    lines.append(
        "SELECTED_ULTIMATE_SLOTTED: "
        + ("PASS" if selected_available else f"FAIL ({selected_display} is not slotted)")
    )
    lines.extend(
        _ultimate_cost_lines(
            database_path=database_path or (get_data_dir() / "eso.db"),
            semantic_id=scenario.selected_ultimate_semantic_id,
        )
    )
    lines.append(
        "ULTIMATE_GENERATION_RULE: successful damaging Light/Heavy Attacks start or "
        "refresh the canonical base-combat Ultimate-generation window; candidate "
        "attack schedules are evaluated rather than converted to a fixed attack count"
    )

    if missing or not selected_available:
        lines.append("BUILD_MATCH: FAIL")
        if missing:
            lines.append("MISSING_REQUIRED_SKILLS: " + ", ".join(missing))
    else:
        lines.append("BUILD_MATCH: PASS")

    lines.append(
        "PROFILE_READY_FOR_CLOCK_SCHEDULING: "
        + ("true" if scenario.ready_for_clock_scheduling else "false")
    )
    if scenario.unresolved:
        lines.append("UNRESOLVED:")
        lines.extend(f"- {item}" for item in scenario.unresolved)
    else:
        lines.append("UNRESOLVED: none")

    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the real Magrat -> DF Healer Lokkestiiz Phase-13 execution profile."
    )
    parser.add_argument(
        "--builds",
        type=Path,
        default=get_data_dir() / "builds.json",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=get_data_dir() / "eso.db",
    )
    args = parser.parse_args()

    try:
        lines = audit(builds_path=args.builds, database_path=args.database)
    except (OSError, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
