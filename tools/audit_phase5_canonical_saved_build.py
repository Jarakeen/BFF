from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.character_build.effect_layer import BarId
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.character_build.support_effect_resolver import (
    CharacterBuildSupportEffectResolver,
    equipped_gear_set_counts,
)
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from models.build_model import PlayerBuild

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _load_saved_build(path: Path, requested: str) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members") if isinstance(payload, dict) else None
    if not isinstance(members, list):
        raise ValueError(f"Unsupported saved-build format in {path}; expected Members")

    key = requested.strip().casefold()
    matches = [
        PlayerBuild.from_dict(entry)
        for entry in members
        if isinstance(entry, dict)
        and str(entry.get("BuildName", "")).strip().casefold() == key
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one saved build named {requested!r}; found {len(matches)}"
        )
    return matches[0]


def _bar_id(value: str) -> BarId:
    return BarId.FRONT if value == "front" else BarId.BACK


def _set_rows(build, active_bar: BarId, repository: GearSetRepository):
    rows: list[tuple[str, int, str]] = []
    for raw_set_id, count in sorted(
        equipped_gear_set_counts(build, active_bar=active_bar).items(),
        key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]),
    ):
        try:
            numeric_id = int(raw_set_id)
        except (TypeError, ValueError):
            rows.append((str(raw_set_id), count, "unknown canonical set id"))
            continue
        record = repository.get_set_by_id(numeric_id)
        rows.append(
            (
                str(raw_set_id),
                count,
                record.name if record is not None else "unknown set",
            )
        )
    return tuple(rows)


def audit_canonical_saved_build(
    *,
    database_path: Path,
    builds_path: Path,
    build_name: str,
    active_bar: str,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2

    try:
        saved = _load_saved_build(builds_path, build_name)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(exc)
        return 3

    adapter = SavedBuildCharacterAdapter(database_path)
    adaptation = adapter.adapt(saved)

    print()
    print("========================================")
    print(" PHASE 5 CANONICAL SAVED-BUILD AUDIT")
    print("========================================")
    print(f"Database:       {database_path}")
    print(f"Saved builds:   {builds_path}")
    print(f"Character:      {saved.Name or '(unnamed)'}")
    print(f"Build:          {saved.BuildName or '(unnamed)'}")
    print(f"Class/Race:     {saved.EsoClass or '(unset)'} / {saved.Race or '(unset)'}")
    print(f"Active bar:     {active_bar}")

    canonical = adaptation.build
    if canonical is None:
        print()
        print("Canonical adaptation: FAILED")
        print("Unresolved diagnostics:")
        for message in adaptation.unresolved or ("No diagnostic supplied.",):
            print(f"  - {message}")
        return 4

    bar_id = _bar_id(active_bar)
    active = canonical.front_bar if bar_id == BarId.FRONT else canonical.back_bar

    print()
    print("Canonical adaptation: CREATED")
    print(f"Canonical name: {canonical.name}")
    print(f"Race id:        {canonical.race_id if canonical.race_id is not None else '(unresolved)'}")
    print(f"Armor pieces:   {len(canonical.armor)}")
    print(f"Mythic:         {'yes' if canonical.mythic is not None else 'no'}")
    print(f"Front bar:      {'resolved' if canonical.front_bar is not None else 'unresolved / absent'}")
    print(f"Back bar:       {'resolved' if canonical.back_bar is not None else 'unresolved / absent'}")
    print(f"Validation:     {'legal' if canonical.is_valid() else 'INVALID'}")

    repository = GearSetRepository(database_path)
    gear_resolver = GearSetEffectVariantResolver(repository)

    print()
    print("Canonical active-bar set counts:")
    set_rows = _set_rows(canonical, bar_id, repository)
    if not set_rows:
        print("  (none)")
    for set_id, count, name in set_rows:
        variants = tuple(gear_resolver.resolve(int(set_id), count)) if set_id.isdigit() else ()
        effect_names = ", ".join(effect.name for effect in variants) or "no registered EffectVariant"
        print(f"  - {name}: {count} pieces | set_id={set_id} | {effect_names}")

    print()
    print("Active canonical bar:")
    if active is None:
        print("  (unresolved / absent)")
    else:
        print(f"  Weapon: {active.main_hand.weapon_type.value}")
        if active.off_hand is not None:
            print(f"  Off hand: {active.off_hand.weapon_type.value}")
        for index, slot in enumerate(active.slots, start=1):
            kind = "ultimate" if slot.is_ultimate else "skill"
            effects = ", ".join(effect.name for effect in slot.effects) or "no EffectVariant"
            print(
                f"  {index}. {slot.skill_id} | {kind} | line={slot.skill_line_id} | {effects}"
            )

    support_resolver = CharacterBuildSupportEffectResolver(
        gear_set_effect_variant_resolver=gear_resolver,
    )
    print()
    print("Canonical support effects on active bar:")
    if active is None or not canonical.is_valid():
        print("  (not resolved because canonical active bar is unavailable or invalid)")
    else:
        registry = support_resolver.resolve(canonical, bar_id)
        effects = registry.all()
        if not effects:
            print("  (none resolved)")
        for effect in effects:
            print(f"  - {effect.name} | source={effect.source}")

    print()
    print("Adapter unresolved diagnostics:")
    if adaptation.unresolved:
        for message in adaptation.unresolved:
            print(f"  - {message}")
    else:
        print("  (none)")

    print()
    print("Audit only: no saved-build data, mappings, or resolver behavior were changed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a saved PlayerBuild through the production CharacterBuild adapter."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        audit_canonical_saved_build(
            database_path=args.database,
            builds_path=args.builds,
            build_name=args.build,
            active_bar=args.active_bar,
        )
    )
