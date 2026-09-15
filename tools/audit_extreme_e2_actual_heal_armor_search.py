from __future__ import annotations

"""Audit the reviewed Extreme H1 armor-weight search boundary.

Read-only. This audit proves the physical Light/Medium/Heavy denominator for the
selected saved build, reports the proof-reduced H1 signatures used by standing
MOST Actual Heal, and exercises each armor-bearing gear-package generator through
the same legality adapter used by the canonical optimizer.

This is deliberately not a claim that the global gear denominator is complete.
It proves armor-weight legality for the current layout and for every package that
the currently reviewed H1 gear generators actually emit. Gear-family discovery
remains a separate E2 coverage boundary.
"""

import argparse
from math import prod
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.build_model import ARMOR_SLOTS, PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.extreme_actual_heal_armor_progression_service import (
    ExtremeActualHealArmorProgressionService,
)
from services.extreme_actual_heal_armor_weight_candidate_service import (
    ExtremeActualHealArmorWeightCandidateService,
)
from services.extreme_actual_heal_armor_weight_legality_service import (
    ExtremeActualHealArmorWeightLegalityService,
)
from services.extreme_actual_heal_armor_weight_package_adapter import (
    ExtremeActualHealArmorWeightPackageAdapter,
)
from services.extreme_actual_heal_double_five_package_service import (
    ExtremeActualHealDoubleFivePackageService,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
)


DEFAULT_CATALOG = get_data_dir() / "characters.json"


def expected_raw_layout_count(
    option_rows: tuple[tuple[str, ...], ...] | list[tuple[str, ...]],
) -> int:
    """Return the exact Cartesian-product denominator for slot weight options."""
    if not option_rows:
        return 0
    lengths = tuple(len(tuple(options)) for options in option_rows)
    if any(length <= 0 for length in lengths):
        return 0
    return int(prod(lengths))


def armor_weight_signature(weights: tuple[str, ...] | list[str]) -> tuple[int, int]:
    """Return the reviewed H1 state: Medium-piece count and distinct type count."""
    normalized = tuple(str(value or "").strip().title() for value in weights)
    return (
        sum(1 for value in normalized if value == "Medium"),
        len(set(normalized)) if normalized else 0,
    )


def _load_saved_build(
    catalog_path: Path,
    *,
    character: str,
    build_name: str,
) -> tuple[PlayerBuild, str, str]:
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
    return PlayerBuild.from_dict(payload), character_id, build_id


def _package_adapters(
    database_path: Path,
    armor_weights: ExtremeActualHealArmorWeightCandidateService,
) -> tuple[tuple[str, ExtremeActualHealArmorWeightPackageAdapter, bool], ...]:
    return (
        (
            "ordinary-five-piece",
            ExtremeActualHealArmorWeightPackageAdapter(
                ExtremeActualHealGearSetCandidateService(database_path),
                armor_weights,
                label="ordinary-five-piece",
            ),
            False,
        ),
        (
            "five-plus-monster",
            ExtremeActualHealArmorWeightPackageAdapter(
                ExtremeActualHealMonsterPackageService(database_path),
                armor_weights,
                label="five-plus-monster",
            ),
            False,
        ),
        (
            "double-five",
            ExtremeActualHealArmorWeightPackageAdapter(
                ExtremeActualHealDoubleFivePackageService(database_path),
                armor_weights,
                label="double-five",
            ),
            False,
        ),
        (
            "ring-mythic-package",
            ExtremeActualHealArmorWeightPackageAdapter(
                ExtremeActualHealMythicPackageService(database_path),
                armor_weights,
                label="ring-mythic-package",
            ),
            True,
        ),
        (
            "non-ring-mythic-package",
            ExtremeActualHealArmorWeightPackageAdapter(
                ExtremeActualHealNonRingMythicPackageService(database_path),
                armor_weights,
                label="non-ring-mythic-package",
            ),
            True,
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", default="Margrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--skip-package-search",
        action="store_true",
        help="Audit only the saved layout denominator and reviewed passive ranks.",
    )
    args = parser.parse_args()

    database_path = Path(args.database)
    build, character_id, build_id = _load_saved_build(
        Path(args.catalog),
        character=args.character,
        build_name=args.build,
    )

    legality_service = ExtremeActualHealArmorWeightLegalityService(database_path)
    armor_weights = ExtremeActualHealArmorWeightCandidateService(legality_service)
    legality = legality_service.evaluate(build)
    frontier = armor_weights.build_candidates(
        build,
        character_id=character_id,
        baseline_build_id=build_id,
    )

    option_rows = tuple(row.allowed_weights for row in legality.slots)
    expected_raw = expected_raw_layout_count(option_rows)
    current_weights = tuple(
        str(build.Armor[slot].get("Weight", "") or "").strip().title()
        for slot in ARMOR_SLOTS
    )
    current_signature = armor_weight_signature(current_weights)
    current_layout_denominator_proven = bool(
        legality.physically_legal
        and frontier.denominator_proven
        and expected_raw > 0
        and frontier.raw_layout_count == expected_raw
    )

    print("EXTREME E2 ACTUAL HEAL ARMOR SEARCH")
    print(f"database={database_path}")
    print(f"character={args.character!r}")
    print(f"build={args.build!r}")
    print(f"active_bar={args.active_bar!r}")
    print(f"armor_slot_count={len(ARMOR_SLOTS)}")
    print(f"current_layout_physically_legal={legality.physically_legal}")
    print(f"current_layout_signature={current_signature}")
    print(f"expected_raw_weight_layout_count={expected_raw}")
    print(f"enumerated_raw_weight_layout_count={frontier.raw_layout_count}")
    print(f"retained_h1_signature_count={frontier.retained_signature_count}")
    print(f"generated_frontier_candidate_count={len(frontier.candidates)}")
    print(f"current_layout_denominator_proven={current_layout_denominator_proven}")
    print("ARMOR SLOT EVIDENCE")
    for row in legality.slots:
        allowed = ",".join(row.allowed_weights) if row.allowed_weights else "NONE"
        print(
            f"  {row.slot}: set={row.set_name!r} current={row.current_weight!r} "
            f"allowed={allowed} legal={row.legal}"
        )
        for item in row.unresolved:
            print(f"    unresolved: {item}")

    print("REVIEWED H1 ARMOR PASSIVE PROGRESSION")
    progression = ExtremeActualHealArmorProgressionService(database_path)
    passive_unresolved: list[str] = []
    for skill_line, passive_name in progression.PASSIVES:
        rank = progression.skill_line_repository.passive_max_rank(passive_name)
        if rank is None or int(rank) <= 0:
            passive_unresolved.append(
                f"Canonical max rank unavailable: {skill_line} / {passive_name}"
            )
            print(f"  {skill_line} / {passive_name}: max_rank=UNRESOLVED")
        else:
            print(f"  {skill_line} / {passive_name}: max_rank={int(rank)}")

    package_unresolved: list[str] = []
    package_denominator_proven = True
    raw_packages = expanded_packages = raw_layouts = retained_signatures = 0
    if args.skip_package_search:
        print("package_search_skipped=True")
        package_denominator_proven = False
    else:
        print("ARMOR-BEARING PACKAGE FRONTIERS")
        for label, adapter, needs_active_bar in _package_adapters(database_path, armor_weights):
            adapter.reset()
            kwargs = {
                "character_id": character_id,
                "baseline_build_id": f"{build_id}:e2-armor:{label}",
            }
            if needs_active_bar:
                kwargs["active_bar"] = args.active_bar
            adapter.build_candidates(build, **kwargs)
            stats = adapter.stats
            raw_packages += stats.raw_package_candidates
            expanded_packages += stats.expanded_candidates
            raw_layouts += stats.raw_weight_layouts_reviewed
            retained_signatures += stats.retained_weight_signatures
            package_unresolved.extend(stats.unresolved)
            if stats.unresolved:
                package_denominator_proven = False
            print(
                f"  {label}: raw_packages={stats.raw_package_candidates} "
                f"expanded={stats.expanded_candidates} "
                f"raw_weight_layouts={stats.raw_weight_layouts_reviewed} "
                f"retained_signatures={stats.retained_weight_signatures} "
                f"unresolved={len(stats.unresolved)}"
            )

    all_unresolved = tuple(
        dict.fromkeys(
            item
            for item in (
                *legality.unresolved,
                *frontier.unresolved,
                *passive_unresolved,
                *package_unresolved,
            )
            if str(item or "").strip()
        )
    )
    package_denominator_proven = bool(
        package_denominator_proven and not args.skip_package_search and not package_unresolved
    )

    print(f"raw_package_candidate_count={raw_packages}")
    print(f"expanded_package_weight_candidate_count={expanded_packages}")
    print(f"package_raw_weight_layouts_reviewed={raw_layouts}")
    print(f"package_retained_h1_signature_count={retained_signatures}")
    print(f"generated_package_armor_legality_proven={package_denominator_proven}")
    print(f"armor_search_unresolved_count={len(all_unresolved)}")
    for item in all_unresolved[:50]:
        print(f"  unresolved: {item}")
    if len(all_unresolved) > 50:
        print(f"  unresolved: ... {len(all_unresolved) - 50} additional items")

    print("GLOBAL_ARMOR_DENOMINATOR_COMPLETE=False")
    print(
        "GLOBAL_ARMOR_DENOMINATOR_REASON=armor legality is proved only for the current layout and currently generated reviewed H1 gear packages; the complete gear-family universe remains a separate E2 boundary"
    )
    local_proof = bool(
        current_layout_denominator_proven
        and not passive_unresolved
        and (args.skip_package_search or package_denominator_proven)
    )
    print(f"e2_h1_reviewed_armor_search_proven={local_proof}")
    print(
        "NEXT_STEP="
        + (
            "close the separate gear-family denominator before promoting armor coverage from reviewed-package proof to global proof"
            if local_proof
            else "close only the reported physical armor/passive evidence gaps; do not treat missing package states as legal"
        )
    )
    return 0 if local_proof else 2


if __name__ == "__main__":
    raise SystemExit(main())
