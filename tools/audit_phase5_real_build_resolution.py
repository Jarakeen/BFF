from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.race_repository import RaceRepository
from minmax.skill_effect_repository import SkillEffectRepository
from models.build_model import PlayerBuild

DEFAULT_BUILDS = get_data_dir() / "builds.json"
DEFAULT_CATALOG = get_data_dir() / "characters.json"

STATUS_RESOLVED = "RESOLVED"
STATUS_CONDITIONAL = "CONDITIONAL"
STATUS_UNRESOLVED = "UNSUPPORTED / UNRESOLVED"
STATUS_MISSING = "MISSING DATA"
STATUS_NA = "NOT APPLICABLE"

_TWO_HANDED_SET_WEAPONS = {
    "bow",
    "two handed",
    "two-handed",
    "fire staff",
    "frost staff",
    "ice staff",
    "lightning staff",
    "shock staff",
    "restoration staff",
}


@dataclass(frozen=True)
class AuditRow:
    source_type: str
    source: str
    status: str
    provider: str
    effect_variant: str
    details: str = ""


def _has_meaningful_data(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, dict):
        return any(_has_meaningful_data(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_meaningful_data(item) for item in value)
    return True


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


def _catalog_build_snapshot(
    path: Path,
    *,
    character_name: str,
    build_name: str,
) -> tuple[bool, bool, str]:
    if not path.exists():
        return False, False, "canonical catalog file does not exist"

    payload = json.loads(path.read_text(encoding="utf-8"))
    builds = payload.get("builds", []) if isinstance(payload, dict) else []
    characters = payload.get("characters", []) if isinstance(payload, dict) else []

    character_ids = {
        str(entry.get("character_id", ""))
        for entry in characters
        if isinstance(entry, dict)
        and str(entry.get("name", "")).strip().casefold()
        == character_name.strip().casefold()
    }
    matches = [
        entry
        for entry in builds
        if isinstance(entry, dict)
        and str(entry.get("name", "")).strip().casefold()
        == build_name.strip().casefold()
        and (
            not character_ids
            or str(entry.get("character_id", "")) in character_ids
        )
    ]
    if len(matches) != 1:
        return False, False, f"expected one canonical build entry; found {len(matches)}"

    legacy = matches[0].get("legacy")
    meaningful = isinstance(legacy, dict) and _has_meaningful_data(
        {
            key: value
            for key, value in legacy.items()
            if key not in {
                "Name",
                "Gamertag",
                "BuildName",
                "Race",
                "EsoClass",
                "Role",
                "CharacterId",
                "BuildId",
            }
        }
    )
    return True, meaningful, "embedded legacy snapshot contains build selections" if meaningful else "embedded legacy snapshot contains identity but no meaningful build selections"


def _audit_progression(build: PlayerBuild) -> CharacterProgression:
    # Read-only carry-forward of the Phase 4 audit assumption. This exists only
    # so current static resolvers can be observed while Phase 5 audits the fact
    # that character-level ownership is not yet persisted canonically.
    armor_lines = {
        f"{str(entry.get('Weight', '') or '').strip().title()} Armor"
        for entry in build.Armor.values()
        if str(entry.get("Weight", "") or "").strip().casefold()
        in {"light", "medium", "heavy"}
    }
    return CharacterProgression(
        attributes=AttributeAllocation(
            health=build.AttributeHealth,
            magicka=build.AttributeMagicka,
            stamina=build.AttributeStamina,
        ),
        owned_skill_lines=tuple(sorted(armor_lines)),
    )


def _relevant_unresolved(build: PlayerBuild, messages: Iterable[str]) -> tuple[str, ...]:
    selected_cp = {
        str(entry.Name or "").strip().casefold()
        for entry in build.ChampionPoints
        if str(entry.Name or "").strip()
    }
    kept: list[str] = []
    seen: set[str] = set()
    for raw in messages:
        message = str(raw or "").strip()
        if not message or message in seen:
            continue
        marker = "Champion Point is dynamic or not yet stat-mapped: "
        if message.startswith(marker):
            name = message[len(marker) :].strip().casefold()
            if name not in selected_cp:
                continue
        seen.add(message)
        kept.append(message)
    return tuple(kept)


def _message_mentions(messages: Iterable[str], name: str) -> str | None:
    key = name.strip().casefold()
    if not key:
        return None
    for message in messages:
        if key in message.casefold():
            return message
    return None


def _variant_status(variants: Iterable[object]) -> str:
    values = tuple(variants)
    if not values:
        return STATUS_UNRESOLVED
    if any(
        getattr(value, "condition", None) is not None
        or getattr(value, "trigger", None) is not None
        for value in values
    ):
        return STATUS_CONDITIONAL
    return STATUS_RESOLVED


def _variant_summary(variants: Iterable[object]) -> str:
    values = tuple(variants)
    if not values:
        return "no EffectVariant resolved"
    return "; ".join(
        f"{getattr(value, 'name', '(unnamed)')}"
        + (f" [condition={getattr(value, 'condition')}]" if getattr(value, "condition", None) else "")
        + (f" [trigger={getattr(value, 'trigger')}]" if getattr(value, "trigger", None) else "")
        for value in values
    )


def _ability_record(database_path: Path, name: str) -> tuple[int, str] | None:
    with sqlite3.connect(database_path) as db:
        columns = {
            str(row[1])
            for row in db.execute("PRAGMA table_info(ability)").fetchall()
        }
        if not {"ability_id", "name"}.issubset(columns):
            return None
        order = "COALESCE(rank, 0) DESC, ability_id DESC" if "rank" in columns else "ability_id DESC"
        row = db.execute(
            f"""
            SELECT ability_id, name
            FROM ability
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            ORDER BY {order}
            LIMIT 1
            """,
            (name,),
        ).fetchone()
    if row is None:
        return None
    return int(row[0]), str(row[1])


def _equipment_entries(build: PlayerBuild) -> list[tuple[str, object]]:
    entries: list[tuple[str, object]] = []
    for slot, value in build.Armor.items():
        entries.append((slot, value))
    entries.extend(
        [
            ("Necklace", build.Necklace),
            ("Ring1", build.Ring1),
            ("Ring2", build.Ring2),
        ]
    )
    return entries


def _entry_value(entry: object, field: str) -> str:
    if isinstance(entry, dict):
        return str(entry.get(field, "") or "").strip()
    return str(getattr(entry, field, "") or "").strip()


def _active_weapon_entries(build: PlayerBuild, active_bar: str) -> tuple[object, object]:
    if active_bar == "front":
        return build.FrontBarWeapon, build.FrontBarOffHand
    return build.BackBarWeapon, build.BackBarOffHand


def _set_counts(build: PlayerBuild, active_bar: str) -> tuple[Counter[str], Counter[str]]:
    # `resolver_counts` mirrors CharacterBuildSupportEffectResolver today:
    # one count per ArmorPiece/Weapon object. `eso_counts` separately exposes
    # the ESO equipment reality that a two-handed weapon occupies two set slots.
    resolver_counts: Counter[str] = Counter()
    eso_counts: Counter[str] = Counter()

    for _slot, entry in _equipment_entries(build):
        set_name = _entry_value(entry, "Set")
        if set_name:
            resolver_counts[set_name] += 1
            eso_counts[set_name] += 1

    for weapon in _active_weapon_entries(build, active_bar):
        set_name = _entry_value(weapon, "Set")
        if not set_name:
            continue
        resolver_counts[set_name] += 1
        weapon_type = _entry_value(weapon, "WeaponType").casefold()
        eso_counts[set_name] += 2 if weapon_type in _TWO_HANDED_SET_WEAPONS else 1

    return resolver_counts, eso_counts


def _print_rows(rows: list[AuditRow]) -> None:
    widths = {
        "type": max([len("TYPE"), *(len(row.source_type) for row in rows)]),
        "source": max([len("SOURCE"), *(len(row.source) for row in rows)]),
        "status": max([len("STATUS"), *(len(row.status) for row in rows)]),
        "variant": max([len("EFFECTVARIANT"), *(len(row.effect_variant) for row in rows)]),
    }
    print(
        f"{'TYPE':<{widths['type']}}  {'SOURCE':<{widths['source']}}  "
        f"{'STATUS':<{widths['status']}}  {'EFFECTVARIANT':<{widths['variant']}}  PROVIDER / DETAILS"
    )
    print("-" * 150)
    for row in rows:
        tail = row.provider
        if row.details:
            tail += f" | {row.details}"
        print(
            f"{row.source_type:<{widths['type']}}  {row.source:<{widths['source']}}  "
            f"{row.status:<{widths['status']}}  {row.effect_variant:<{widths['variant']}}  {tail}"
        )


def audit_real_build_resolution(
    *,
    database_path: Path,
    builds_path: Path,
    catalog_path: Path,
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
        build = _load_saved_build(builds_path, build_name)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(exc)
        return 3

    progression = _audit_progression(build)
    context = BuildCalculationContextFactory(
        race_repository=RaceRepository(database_path),
        gear_set_repository=GearSetRepository(database_path),
    ).build(
        character_id=build.Name.strip() or build.Gamertag.strip() or "saved-character",
        build_id=build.BuildName.strip() or "saved-build",
        build=build,
        progression=progression,
        active_bar=active_bar,
    )
    unresolved = _relevant_unresolved(
        build,
        tuple(context.unresolved_gear_effects),
    )

    catalog_found, catalog_meaningful, catalog_detail = _catalog_build_snapshot(
        catalog_path,
        character_name=build.Name,
        build_name=build.BuildName,
    )

    rows: list[AuditRow] = []
    rows.append(
        AuditRow(
            "Persistence",
            "canonical saved build",
            STATUS_RESOLVED if catalog_found and catalog_meaningful else STATUS_MISSING,
            "services.canonical_build_bridge.CanonicalBuildBridge",
            "NO",
            catalog_detail,
        )
    )
    rows.append(
        AuditRow(
            "Ownership",
            "skill-line/passive ownership",
            STATUS_MISSING,
            "CharacterProgression (audit inference only)",
            "NO",
            "armor lines inferred read-only: "
            + (", ".join(progression.owned_skill_lines) if progression.owned_skill_lines else "none"),
        )
    )

    static_sources = [
        ("Race", build.Race, "BuildCalculationContextFactory / RaceRepository"),
        ("Class", build.EsoClass, "BuildCalculationContextFactory / passive input resolvers"),
        (
            "Attributes",
            f"H{build.AttributeHealth}/M{build.AttributeMagicka}/S{build.AttributeStamina}",
            "BuildCalculationContextFactory / CharacterProgression",
        ),
        ("Mundus", build.Mundus, "BuildCalculationContextFactory"),
        ("Food", build.Food, "BuildCalculationContextFactory"),
        ("Potion", build.Potion, "BuildCalculationContextFactory"),
    ]
    for source_type, source, provider in static_sources:
        if not str(source).strip():
            rows.append(AuditRow(source_type, "(none)", STATUS_NA, provider, "NO"))
            continue
        warning = _message_mentions(unresolved, str(source))
        rows.append(
            AuditRow(
                source_type,
                str(source),
                STATUS_UNRESOLVED if warning else STATUS_RESOLVED,
                provider,
                "NO",
                warning or "resolved through standing/static build context, not EffectVariant",
            )
        )

    for cp in build.ChampionPoints:
        name = str(cp.Name or "").strip()
        if not name:
            continue
        warning = _message_mentions(unresolved, name)
        rows.append(
            AuditRow(
                "Champion Point",
                name,
                STATUS_UNRESOLVED if warning else STATUS_RESOLVED,
                "BuildCalculationContextFactory / CP input resolvers",
                "NO",
                warning or "no build-relevant unresolved diagnostic from standing context",
            )
        )

    for slot, entry in _equipment_entries(build):
        trait = _entry_value(entry, "Trait")
        enchant = _entry_value(entry, "Enchant")
        if trait:
            warning = _message_mentions(unresolved, trait)
            rows.append(
                AuditRow(
                    "Trait",
                    f"{slot}: {trait}",
                    STATUS_UNRESOLVED if warning else STATUS_RESOLVED,
                    "BuildCalculationContextFactory / gear input resolvers",
                    "NO",
                    warning or "standing/static gear path",
                )
            )
        if enchant:
            warning = _message_mentions(unresolved, enchant)
            rows.append(
                AuditRow(
                    "Enchant",
                    f"{slot}: {enchant}",
                    STATUS_UNRESOLVED if warning else STATUS_RESOLVED,
                    "BuildCalculationContextFactory / gear input resolvers",
                    "NO",
                    warning or "standing/static gear path",
                )
            )

    gear_repository = GearSetRepository(database_path)
    gear_resolver = GearSetEffectVariantResolver(gear_repository)
    resolver_counts, eso_counts = _set_counts(build, active_bar)
    for set_name in sorted(eso_counts, key=str.casefold):
        gear_set = gear_repository.get_set(set_name)
        if gear_set is None:
            rows.append(
                AuditRow(
                    "Gear Set",
                    set_name,
                    STATUS_MISSING,
                    "GearSetRepository",
                    "YES",
                    "selected set name not found in gear_set",
                )
            )
            continue
        resolver_count = resolver_counts[set_name]
        expected_count = eso_counts[set_name]
        variants = tuple(gear_resolver.resolve(gear_set.id, resolver_count))
        count_note = f"resolver count={resolver_count}; ESO equipped count={expected_count}"
        if resolver_count != expected_count:
            count_note += "; two-handed weapon set count mismatch can hide higher-tier bonuses"
        rows.append(
            AuditRow(
                "Gear Set",
                set_name,
                _variant_status(variants),
                "GearSetRepository -> GearSetEffectVariantResolver",
                "YES",
                f"{count_note}; {_variant_summary(variants)}",
            )
        )

    skill_repository = SkillEffectRepository(database_path)
    skills = build.FrontBarSkills if active_bar == "front" else build.BackBarSkills
    for skill_name in skills:
        name = str(skill_name or "").strip()
        if not name:
            continue
        record = _ability_record(database_path, name)
        if record is None:
            rows.append(
                AuditRow(
                    "Skill",
                    name,
                    STATUS_MISSING,
                    "ability table -> SkillEffectRepository",
                    "YES",
                    "no exact-name ability record",
                )
            )
            continue
        ability_id, canonical_name = record
        variants = tuple(skill_repository.resolve(ability_id))
        rows.append(
            AuditRow(
                "Skill",
                name,
                _variant_status(variants),
                "SkillEffectRepository",
                "YES",
                f"ability_id={ability_id} ({canonical_name}); {_variant_summary(variants)}",
            )
        )

    for weapon_label, weapon in zip(
        (f"{active_bar} main hand", f"{active_bar} off hand"),
        _active_weapon_entries(build, active_bar),
    ):
        weapon_type = _entry_value(weapon, "WeaponType")
        if not weapon_type:
            continue
        enchant = _entry_value(weapon, "Enchant")
        rows.append(
            AuditRow(
                "Weapon",
                f"{weapon_label}: {weapon_type}",
                STATUS_RESOLVED,
                "BuildCalculationContextFactory; CharacterBuildSupportEffectResolver has a separate legacy enchant bridge",
                "MIXED",
                f"weapon enchant={enchant or '(none)'}; full saved-build -> CharacterBuild adapter not present",
            )
        )

    print()
    print("========================================")
    print(" PHASE 5 REAL BUILD RESOLUTION AUDIT")
    print("========================================")
    print(f"Database:       {database_path}")
    print(f"Saved builds:   {builds_path}")
    print(f"Catalog:        {catalog_path}")
    print(f"Character:      {build.Name or '(unnamed)'}")
    print(f"Build:          {build.BuildName or '(unnamed)'}")
    print(f"Class/Race:     {build.EsoClass or '(unset)'} / {build.Race or '(unset)'}")
    print(f"Active bar:     {active_bar}")
    print()
    print("Classification matrix:")
    _print_rows(rows)

    print()
    print("Build-relevant unresolved diagnostics:")
    if unresolved:
        for message in unresolved:
            print(f"  - {message}")
    else:
        print("  (none from standing BuildCalculationContext)")

    print()
    print("Architectural findings:")
    if not catalog_found or not catalog_meaningful:
        print("  - Canonical catalog does not currently carry this populated saved build authoritatively.")
    print("  - No production saved PlayerBuild -> canonical CharacterBuild adapter was exercised by this audit.")
    print("  - Gear effects were queried through GearSetEffectVariantResolver without adding mappings.")
    print("  - Skill effects were queried through SkillEffectRepository without adding mappings.")
    print("  - Standing character-sheet effects remain separate from EffectVariant and are labeled as such.")
    if resolver_counts != eso_counts:
        mismatches = [
            f"{name}: resolver={resolver_counts[name]}, ESO={eso_counts[name]}"
            for name in sorted(eso_counts, key=str.casefold)
            if resolver_counts[name] != eso_counts[name]
        ]
        print("  - Current CharacterBuild gear-set counting disagrees with ESO two-handed set counting: " + "; ".join(mismatches))
    print()
    print("Audit only: no effect rules, mappings, persistence, or resolver behavior were changed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit Phase 5 real saved-build resolution without patching missing effects."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        audit_real_build_resolution(
            database_path=args.database,
            builds_path=args.builds,
            catalog_path=args.catalog,
            build_name=args.build,
            active_bar=args.active_bar,
        )
    )
