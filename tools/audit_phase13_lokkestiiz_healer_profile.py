from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from services.build_service import BuildService
from services.rotation_lokkestiiz_healer_execution_profile import (
    build_magrat_df_healer_lokkestiiz_profile,
)


def _semantic_id(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


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


def audit(*, builds_path: Path) -> tuple[str, ...]:
    profile = build_magrat_df_healer_lokkestiiz_profile()
    roster = BuildService(builds_path).load()
    build = _find_build(
        roster,
        character_name=profile.character_name,
        build_name=profile.build_name,
    )
    slotted = _slotted_skill_map(build)

    lines: list[str] = []
    lines.append("PHASE 13 LOKKESTIIZ HEALER EXECUTION AUDIT")
    lines.append(f"BUILD: {profile.character_name} -> {profile.build_name}")
    lines.append(f"ENCOUNTER: {profile.encounter_id}")
    lines.append(f"REQUESTED_CYCLES: {profile.requested_cycles}")
    lines.append(
        "CANONICAL_FLIGHT_TRIGGERS: "
        + ", ".join(f"{value}%" for value in profile.canonical_flight_health_thresholds)
    )

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

    if missing:
        lines.append("BUILD_MATCH: FAIL")
        lines.append("MISSING_REQUIRED_SKILLS: " + ", ".join(missing))
    else:
        lines.append("BUILD_MATCH: PASS")

    lines.append(
        "PROFILE_READY_FOR_CLOCK_SCHEDULING: "
        + ("true" if profile.ready_for_clock_scheduling else "false")
    )
    if profile.unresolved:
        lines.append("UNRESOLVED:")
        lines.extend(f"- {item}" for item in profile.unresolved)
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
    args = parser.parse_args()

    try:
        lines = audit(builds_path=args.builds)
    except (OSError, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
