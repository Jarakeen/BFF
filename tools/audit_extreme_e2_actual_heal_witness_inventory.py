from __future__ import annotations

"""Inventory real saved-build healing witnesses for E2 CP scoring.

This audit is read-only. It evaluates every slotted skill on the saved build
through the same canonical actual-heal event path used by the E2 CP scoring
audit, so a CP scoring witness can be selected only when critical eligibility
and all other event semantics are actually resolved.
"""

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)
from services.extreme_complete_optimization_service import (
    ExtremeCompleteOptimizationService,
)
from services.minmax_character_progression_adapter import (
    MinmaxCharacterProgressionAdapter,
)


DEFAULT_CATALOG = get_data_dir() / "characters.json"


def _identity(value: object) -> str:
    text = str(value or "").strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _load_saved_build(
    catalog_path: Path,
    *,
    character: str,
    build_name: str,
) -> tuple[PlayerBuild, str, str, BuildCatalogService]:
    service = BuildCatalogService(catalog_path)
    catalog = service.load()
    matches = [
        row
        for row in catalog.get("characters", ())
        if isinstance(row, dict)
        and str(row.get("name") or "").strip().casefold() == character.casefold()
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Canonical character not found uniquely: {character!r}; matches={len(matches)}"
        )
    character_id = str(matches[0].get("character_id") or "").strip()
    builds = [
        row
        for row in service.builds_for_character(character_id)
        if str(row.get("name") or "").strip().casefold() == build_name.casefold()
    ]
    if len(builds) != 1:
        raise ValueError(
            f"Canonical build not found uniquely: character={character!r} build={build_name!r}; matches={len(builds)}"
        )
    record = builds[0]
    payload = record.get("payload") or record.get("legacy")
    if not isinstance(payload, dict):
        raise ValueError("Canonical build payload is unavailable")
    build_id = str(record.get("build_id") or "").strip()
    if not build_id:
        raise ValueError("Canonical build_id is unavailable")
    return PlayerBuild.from_dict(payload), character_id, build_id, service


def _slotted(build: PlayerBuild) -> tuple[tuple[str, str, str], ...]:
    rows: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for bar, skills in (
        ("front", build.FrontBarSkills),
        ("back", build.BackBarSkills),
    ):
        for raw in skills:
            display = str(raw or "").strip()
            if not display:
                continue
            entity_id = _identity(display)
            key = (bar, entity_id)
            if key in seen:
                continue
            seen.add(key)
            rows.append((bar, display, entity_id))
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", default="Margrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    build, character_id, build_id, catalog_service = _load_saved_build(
        Path(args.catalog),
        character=args.character,
        build_name=args.build,
    )
    database_path = Path(args.database)
    optimizer = ExtremeCanonicalActualHealOptimizationService(
        optimizer=ExtremeCompleteOptimizationService(database_path=database_path)
    )
    progression_resolution = MinmaxCharacterProgressionAdapter(catalog_service).resolve(build)
    if not progression_resolution.resolved:
        raise ValueError("; ".join(progression_resolution.unresolved))
    if progression_resolution.character_id != character_id:
        raise ValueError(
            "Saved-build progression resolved to a different canonical character: "
            f"catalog={character_id!r} progression={progression_resolution.character_id!r}"
        )

    cache = {}
    rows = []
    for bar, display, entity_id in _slotted(build):
        event, unresolved = optimizer._evaluate_cached(
            build,
            progression=progression_resolution.progression,
            character_id=character_id,
            build_id=f"{build_id}:e2-heal-witness:{bar}:{entity_id}",
            entity_id=entity_id,
            active_bar=bar,
            evaluation_cache=cache,
        )
        combined_unresolved = tuple(
            dict.fromkeys(
                item
                for item in (*event.unresolved, *unresolved)
                if str(item or "").strip()
            )
        )
        witness_ready = event.critical_heal is not None and not combined_unresolved
        rows.append(
            (
                bar,
                display,
                entity_id,
                event.normal_heal,
                event.critical_heal,
                combined_unresolved,
                witness_ready,
            )
        )

    ready_rows = [row for row in rows if row[-1]]

    print("EXTREME E2 ACTUAL HEAL WITNESS INVENTORY")
    print(f"database={database_path}")
    print(f"catalog={Path(args.catalog)}")
    print(f"character={args.character!r}")
    print(f"character_id={character_id!r}")
    print(f"build={args.build!r}")
    print(f"build_id={build_id!r}")
    print()
    print("SLOTTED SKILL RESULTS")
    for bar, display, entity_id, normal, critical, unresolved, witness_ready in rows:
        print(
            f"  bar={bar} | skill={display!r} | entity={entity_id!r} | "
            f"normal={normal!r} | critical={critical!r} | witness_ready={witness_ready}"
        )
        for item in unresolved:
            print(f"    unresolved: {item}")
    print()
    print("PROOF STATUS")
    print(f"slotted_skill_count={len(rows)}")
    print(f"critical_witness_count={len(ready_rows)}")
    if ready_rows:
        print(f"recommended_entity={ready_rows[0][2]!r}")
        print(f"recommended_bar={ready_rows[0][0]!r}")
        print("e2_actual_heal_witness_available=True")
        print(
            "NEXT_STEP=rerun the E2 CP scoring audit with recommended_entity; "
            "do not import or infer critical eligibility for unresolved skills"
        )
        return 0

    print("recommended_entity=None")
    print("recommended_bar=None")
    print("e2_actual_heal_witness_available=False")
    print(
        "NEXT_STEP=close the canonical critical-evidence corpus gap for at least one real saved-build heal before claiming CP scoring complete"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
