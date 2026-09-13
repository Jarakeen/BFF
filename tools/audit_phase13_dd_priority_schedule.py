from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationActionKind
from tools.audit_phase13_saved_build_rotation_timing import _load_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


def _ordinary_skill_slots(values) -> tuple[tuple[int, str], ...]:
    return tuple(
        (slot, str(value).strip())
        for slot, value in enumerate(list(values or [])[:5], start=1)
        if str(value or "").strip()
    )


def _parse_priority(raw: str, *, build) -> AbilityPriorityEntry:
    text = str(raw or "").strip()
    parts = text.split(":")
    if len(parts) != 3:
        raise ValueError(
            f"ability priority must use BAR:SLOT:PRIORITY, got {raw!r}"
        )

    bar = parts[0].strip().casefold()
    if bar not in {"front", "back"}:
        raise ValueError(f"ability priority bar must be front or back, got {parts[0]!r}")

    try:
        slot = int(parts[1])
        priority = int(parts[2])
    except ValueError as exc:
        raise ValueError(
            f"ability priority slot and priority must be integers, got {raw!r}"
        ) from exc

    values = (
        getattr(build, "FrontBarSkills", [])
        if bar == "front"
        else getattr(build, "BackBarSkills", [])
    )
    by_slot = dict(_ordinary_skill_slots(values))
    skill_name = by_slot.get(slot)
    if skill_name is None:
        raise ValueError(
            f"saved build has no ordinary skill in {bar} slot {slot}; cannot assign priority"
        )

    return AbilityPriorityEntry(
        bar=bar,
        slot=slot,
        skill_name=skill_name,
        priority=priority,
    )


def _priority_entries(raw_values: tuple[str, ...], *, build) -> tuple[AbilityPriorityEntry, ...]:
    supplied = {
        (entry.bar, entry.slot): entry
        for entry in (_parse_priority(raw, build=build) for raw in raw_values)
    }

    required: list[AbilityPriorityEntry] = []
    for bar, values in (
        ("front", getattr(build, "FrontBarSkills", [])),
        ("back", getattr(build, "BackBarSkills", [])),
    ):
        for slot, skill_name in _ordinary_skill_slots(values):
            entry = supplied.get((bar, slot))
            if entry is None:
                raise ValueError(
                    "explicit priority audit requires every ordinary saved slot to be ranked; "
                    f"missing {bar} slot {slot}: {skill_name}"
                )
            required.append(entry)

    extras = sorted(set(supplied) - {(entry.bar, entry.slot) for entry in required})
    if extras:
        raise ValueError(f"priority entries target non-ordinary saved slots: {extras!r}")
    return tuple(required)


def _print_saved_slots(build) -> None:
    print("SAVED ORDINARY SKILLS")
    print("---------------------")
    for bar, values in (
        ("front", getattr(build, "FrontBarSkills", [])),
        ("back", getattr(build, "BackBarSkills", [])),
    ):
        slots = _ordinary_skill_slots(values)
        if not slots:
            print(f"{bar}: none")
            continue
        for slot, skill_name in slots:
            print(f"{bar}:{slot} | {skill_name}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one saved DD rotation with explicit canonical ability priorities "
            "and report the resulting schedule/unresolved diagnostics."
        )
    )
    parser.add_argument("--character")
    parser.add_argument("--build", required=True)
    parser.add_argument("--builds", type=Path, default=ROOT / "data" / "builds.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--priority",
        action="append",
        default=[],
        metavar="BAR:SLOT:PRIORITY",
        help=(
            "Rank one ordinary saved-bar slot. Lower numbers are higher priority. "
            "Supply every occupied ordinary slot."
        ),
    )
    parser.add_argument(
        "--list-slots",
        action="store_true",
        help="Print ordinary saved slots for the selected build and exit.",
    )
    parser.add_argument(
        "--no-weave",
        action="store_true",
        help="Disable normal light-attack weaving for this diagnostic generation.",
    )
    args = parser.parse_args()

    duration = float(args.duration)
    if duration <= 0:
        raise ValueError("duration must be positive")

    build = _load_build(Path(args.builds), args.build, args.character)
    role = str(getattr(build, "Role", "") or "").strip().casefold()
    if role not in _DD_ROLE_KEYS:
        raise ValueError(
            "DD priority schedule audit requires a saved damage-dealer build; "
            f"got role={getattr(build, 'Role', '')!r}"
        )

    if args.list_slots:
        _print_saved_slots(build)
        return 0

    priorities = _priority_entries(tuple(args.priority or ()), build=build)
    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=duration,
            weave_light_attacks=not bool(args.no_weave),
            ability_priorities=priorities,
        ),
    )

    print("=" * 72)
    print(" PHASE 13 DD EXPLICIT-PRIORITY SCHEDULE AUDIT")
    print("=" * 72)
    print(f"Character: {_character_name(build) or 'unnamed'}")
    print(f"Build:     {getattr(build, 'BuildName', '') or 'unnamed'}")
    print(f"Duration:  {duration:g}s")
    print()

    print("PRIORITIES")
    print("----------")
    for entry in sorted(priorities, key=lambda item: (item.priority, item.bar, item.slot)):
        print(
            f"{entry.priority:3d} | {entry.bar}:{entry.slot} | {entry.skill_name}"
        )
    print()

    waits = [action for action in generated.plan.actions if action.kind is RotationActionKind.WAIT]
    skills = [action for action in generated.plan.actions if action.kind is RotationActionKind.SKILL]
    print("SCHEDULE")
    print("--------")
    print(f"Skill actions: {len(skills)}")
    print(f"Wait actions:  {len(waits)}")
    print()

    print("PLAN-LEVEL UNRESOLVED")
    print("---------------------")
    if generated.plan.unresolved:
        for item in generated.plan.unresolved:
            print(item)
    else:
        print("none")
    print()
    print(
        "Interpretation: explicit priorities are caller-owned gameplay intent. This audit "
        "does not infer an optimal rotation; it verifies how the canonical scheduler uses "
        "a supplied complete ranking across seed order, due refreshes, and persistent-toggle fillers."
    )
    return 0


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


if __name__ == "__main__":
    raise SystemExit(main())
