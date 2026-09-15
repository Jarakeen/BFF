from __future__ import annotations

"""Audit the complete legal 64-point attribute denominator for Extreme H1.

Read-only. The production H1 optimizer currently proposes only the three pure
64-point allocations during coordinate search. This audit enumerates every legal
Health/Magicka/Stamina split so E2 can measure the real denominator before any
objective-specific dominance pruning is accepted.

The audit can optionally score one saved-build healing event by normal-heal value.
That score is useful for the selected event's attribute frontier even when positive
critical-heal evidence is not yet available. It does NOT by itself prove the H1
critical-event global maximum or a universal pure-allocation dominance rule.
"""

import argparse
from dataclasses import replace
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.character_progression import AttributeAllocation
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


DEFAULT_CATALOG = get_data_dir() / "characters.json"
ATTRIBUTE_POINT_TOTAL = 64


def legal_attribute_allocations(
    total_points: int = ATTRIBUTE_POINT_TOTAL,
) -> tuple[tuple[int, int, int], ...]:
    total = int(total_points)
    if total < 0:
        raise ValueError("attribute point total must be non-negative")
    return tuple(
        (health, magicka, total - health - magicka)
        for health in range(total + 1)
        for magicka in range(total - health + 1)
    )


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


def _active_bar_for_entity(build: PlayerBuild, entity_id: str) -> str:
    wanted = _identity(entity_id)
    matches: list[str] = []
    for bar, skills in (("front", build.FrontBarSkills), ("back", build.BackBarSkills)):
        if any(_identity(skill) == wanted for skill in skills if str(skill or "").strip()):
            matches.append(bar)
    if not matches:
        raise ValueError(f"Healing entity is not slotted on the saved build: {entity_id!r}")
    return "front" if "front" in matches else matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", default="Margrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--entity", default="combat_prayer")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--denominator-only",
        action="store_true",
        help="Report the legal allocation denominator without evaluating a heal event.",
    )
    args = parser.parse_args()

    allocations = legal_attribute_allocations()
    expected_count = (ATTRIBUTE_POINT_TOTAL + 1) * (ATTRIBUTE_POINT_TOTAL + 2) // 2
    denominator_proven = (
        len(allocations) == expected_count
        and len(set(allocations)) == expected_count
        and all(sum(row) == ATTRIBUTE_POINT_TOTAL and min(row) >= 0 for row in allocations)
    )

    print("EXTREME E2 ACTUAL HEAL ATTRIBUTE DENOMINATOR")
    print(f"attribute_point_total={ATTRIBUTE_POINT_TOTAL}")
    print(f"expected_legal_allocation_count={expected_count}")
    print(f"enumerated_legal_allocation_count={len(allocations)}")
    print(f"attribute_denominator_proven={denominator_proven}")

    if args.denominator_only:
        print("scoring_skipped=True")
        print(
            "NEXT_STEP=score the full denominator for a canonical heal witness before accepting any pure-allocation dominance pruning"
        )
        return 0 if denominator_proven else 2

    build, character_id, build_id, catalog_service = _load_saved_build(
        Path(args.catalog),
        character=args.character,
        build_name=args.build,
    )
    entity_id = _identity(args.entity)
    active_bar = _active_bar_for_entity(build, entity_id)
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
    scored: list[tuple[float, tuple[int, int, int]]] = []
    unresolved: list[str] = []
    for health, magicka, stamina in allocations:
        candidate = PlayerBuild.from_dict(build.to_dict())
        candidate.AttributeHealth = health
        candidate.AttributeMagicka = magicka
        candidate.AttributeStamina = stamina
        progression = replace(
            progression_resolution.progression,
            attributes=AttributeAllocation(
                health=health,
                magicka=magicka,
                stamina=stamina,
            ),
        )
        event, candidate_unresolved = optimizer._evaluate_cached(
            candidate,
            progression=progression,
            character_id=character_id,
            build_id=f"{build_id}:e2-attributes:{health}:{magicka}:{stamina}",
            entity_id=entity_id,
            active_bar=active_bar,
            evaluation_cache=cache,
        )
        if event.normal_heal is None:
            unresolved.append(
                f"attributes={health}/{magicka}/{stamina}: canonical normal heal unresolved"
            )
            unresolved.extend(
                f"attributes={health}/{magicka}/{stamina}: {item}"
                for item in (*event.unresolved, *candidate_unresolved)
                if str(item or "").strip()
            )
            continue
        scored.append((float(event.normal_heal), (health, magicka, stamina)))

    scored.sort(key=lambda row: (-row[0], row[1]))
    unresolved = list(dict.fromkeys(unresolved))
    winner = scored[0] if scored else None
    pure_allocations = {
        (ATTRIBUTE_POINT_TOTAL, 0, 0),
        (0, ATTRIBUTE_POINT_TOTAL, 0),
        (0, 0, ATTRIBUTE_POINT_TOTAL),
    }

    print(f"character={args.character!r}")
    print(f"build={args.build!r}")
    print(f"entity_id={entity_id!r}")
    print(f"active_bar={active_bar!r}")
    print(f"scored_allocation_count={len(scored)}")
    print(f"scoring_unresolved_count={len(unresolved)}")
    if winner is not None:
        print(f"winner_normal_heal={winner[0]:.6f}")
        print(f"winner_attributes={winner[1]}")
        print(f"winner_is_pure_allocation={winner[1] in pure_allocations}")
    else:
        print("winner_normal_heal=None")
        print("winner_attributes=None")
        print("winner_is_pure_allocation=False")
    for item in unresolved[:25]:
        print(f"  unresolved: {item}")
    if len(unresolved) > 25:
        print(f"  unresolved: ... {len(unresolved) - 25} additional items")

    scoring_complete = denominator_proven and len(scored) == len(allocations) and not unresolved
    print(f"e2_actual_heal_attribute_scoring_complete={scoring_complete}")
    print(
        "NEXT_STEP="
        + (
            "compare winners across representative heal scaling families before replacing exhaustive allocation search with a dominance rule"
            if scoring_complete
            else "close only the reported canonical normal-heal scoring blockers; do not infer missing allocation scores"
        )
    )
    return 0 if scoring_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
