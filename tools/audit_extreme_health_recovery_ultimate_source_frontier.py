from __future__ import annotations

"""Inventory the U50 Ultimate-generation source frontier for the Health Recovery route."""

import argparse
from collections import Counter
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.ultimate_source_loadout_combination_service import (
    UltimateSourceLoadoutCandidate,
    UltimateSourceLoadoutCombinationService,
)
from services.ultimate_source_reference_frontier_service import (
    UltimateSourceReferenceFrontierService,
    UltimateSourceRouteStatus,
)
from services.ultimate_source_runtime_legality_service import (
    UltimateSourceRuntimeLegalityService,
    UltimateSourceRuntimeStatus,
)


DEFAULT_SOURCE = ROOT / "math" / "ESO Ultimate Generation Calculator _ U50 _ Hyperioxes.htm"

_TRIGGER_WITNESSES = {
    "blessing_peak": (1.0, 7.0, 13.0, 19.0),
    "bloodspawn": (1.0, 6.0, 11.0, 16.0, 21.0),
    "baron_zaudrus": tuple(float(value) for value in range(1, 25)),
    "hide_of_the_werewolf": (1.0, 6.0, 11.0, 16.0, 21.0),
    "arkasis": (1.0,),
    "arkays_charity": (1.0, 10.0, 19.0),
    "exhilarating_drain": tuple(float(value) for value in range(2, 25)),
    "decisive": (
        *(float(value) for value in range(1, 25)),
        *(1.5 * float(value) for value in range(1, 17)),
    ),
}

_SET_REQUIREMENTS = {
    "bloodspawn": ("Bloodspawn", 2),
    "baron_zaudrus": ("Baron Zaudrus", 2),
    "hide_of_the_werewolf": ("Hide of the Werewolf", 5),
    "arkasis": ("Arkasis's Genius", 5),
    "arkays_charity": ("Arkay's Charity", 5),
}
_STOCHASTIC_SOURCE_IDS = frozenset({"bloodspawn", "decisive"})
_ACTION_PROOF_SOURCE_IDS = frozenset({"baron_zaudrus"})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    return parser


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _canonical_matches(
    database: Path,
    label: str,
    source_id: str | None = None,
) -> tuple[str, ...]:
    if not database.is_file():
        return ()
    matches: list[str] = []
    with sqlite3.connect(database) as db:
        skill_columns = _columns(db, "skill")
        if {"name", "description"}.issubset(skill_columns):
            class_expr = "COALESCE(class_type, '')" if "class_type" in skill_columns else "''"
            line_expr = "COALESCE(skill_line, '')" if "skill_line" in skill_columns else "''"
            rows = db.execute(
                f"""
                SELECT name, {class_expr}, {line_expr}, COALESCE(description, '')
                FROM skill
                WHERE LOWER(COALESCE(name, '')) = LOWER(?)
                ORDER BY id
                """,
                (label,),
            ).fetchall()
            matches.extend(
                f"skill name={name!r} class={class_name!r} line={line!r} description={description!r}"
                for name, class_name, line, description in rows
            )

        if source_id == "exhilarating_drain" and {
            "name", "description"
        }.issubset(skill_columns):
            vampire_line = (
                "LOWER(COALESCE(skill_line, '')) LIKE '%vampire%'"
                if "skill_line" in skill_columns
                else "0"
            )
            rows = db.execute(
                f"""
                SELECT name, {line_expr}, COALESCE(description, '')
                FROM skill
                WHERE ({vampire_line})
                  AND LOWER(COALESCE(description, '')) LIKE '%health recovery%'
                ORDER BY id
                """
            ).fetchall()
            matches.extend(
                f"vampire_cost name={name!r} line={line!r} description={description!r}"
                for name, line, description in rows
            )

        ability_columns = _columns(db, "ability")
        if {"name", "index_name", "description"}.issubset(ability_columns):
            duration_expr = "COALESCE(duration, 0)" if "duration" in ability_columns else "0"
            rows = db.execute(
                f"""
                SELECT name, index_name, COALESCE(description, ''), {duration_expr}
                FROM ability
                WHERE LOWER(COALESCE(name, '')) = LOWER(?)
                   OR LOWER(COALESCE(index_name, '')) = LOWER(?)
                ORDER BY ability_id
                """,
                (label, source_id or ""),
            ).fetchall()
            matches.extend(
                f"ability name={name!r} index_name={index_name!r} duration={duration!r} description={description!r}"
                for name, index_name, description, duration in rows
            )

        trait_columns = _columns(db, "weapon_trait_effect")
        if source_id == "decisive" and {
            "material_name", "effect_type", "value", "secondary_value", "unit", "description"
        }.issubset(trait_columns):
            rows = db.execute(
                """
                SELECT material_name, effect_type, value, secondary_value, unit,
                       COALESCE(description, '')
                FROM weapon_trait_effect
                WHERE effect_type = 'ultimate_gain_chance'
                ORDER BY id
                """
            ).fetchall()
            matches.extend(
                f"weapon_trait material={material!r} effect_type={effect_type!r} "
                f"value={value!r} secondary_value={secondary!r} unit={unit!r} "
                f"description={description!r}"
                for material, effect_type, value, secondary, unit, description in rows
            )

        gear_columns = _columns(db, "gear_set")
        bonus_columns = _columns(db, "gear_set_bonus")
        if {"id", "name"}.issubset(gear_columns) and {"set_id", "piece_count", "description"}.issubset(bonus_columns):
            rows = db.execute(
                """
                SELECT gs.name, gsb.piece_count, gsb.description
                FROM gear_set gs JOIN gear_set_bonus gsb ON gsb.set_id = gs.id
                WHERE LOWER(COALESCE(gs.name, '')) = LOWER(?)
                ORDER BY gsb.piece_count, gsb.id
                """,
                (label,),
            ).fetchall()
            matches.extend(
                f"gear name={name!r} pieces={pieces} description={description!r}"
                for name, pieces, description in rows
            )
    return tuple(matches)


def main() -> int:
    args = _parser().parse_args()
    database, source = Path(args.database), Path(args.source)
    if not source.is_file():
        print(f"source_missing={source}")
        return 2

    rows = UltimateSourceReferenceFrontierService.parse(
        source.read_text(encoding="utf-8", errors="replace")
    )
    counts = Counter(row.route_status.value for row in rows)

    print("EXTREME HEALTH RECOVERY ULTIMATE SOURCE FRONTIER")
    print(f"database={database}")
    print(f"source={source}")
    print("route=Khajiit pure Dragonknight with Booming Voice")
    print("required_additional_ultimate=114.000")
    print(f"reference_sources_reviewed={len(rows)}")
    print("status_counts=" + ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())))
    print()

    for row in rows:
        print(
            f"{row.source_id}: label={row.label!r} category={row.category!r} "
            f"displayed_rate={row.displayed_rate!r} status={row.route_status.value}"
        )
        print(f"  reason={row.reason}")
        if row.route_status in {
            UltimateSourceRouteStatus.SEARCH_STATE_MUTATION,
            UltimateSourceRouteStatus.EXACT_REVIEW_REQUIRED,
        }:
            matches = _canonical_matches(database, row.label, row.source_id)
            if matches:
                for match in matches:
                    print(f"  canonical={match}")
            else:
                print("  canonical=<no exact name match in reviewed skill/gear tables>")

    candidates = tuple(
        row for row in rows
        if row.route_status in {
            UltimateSourceRouteStatus.SEARCH_STATE_MUTATION,
            UltimateSourceRouteStatus.EXACT_REVIEW_REQUIRED,
        }
    )
    reviews = tuple(
        (
            row,
            UltimateSourceRuntimeLegalityService.review(
                row.source_id,
                canonical_records=_canonical_matches(database, row.label, row.source_id),
                trigger_seconds=_TRIGGER_WITNESSES.get(row.source_id, ()),
            ),
        )
        for row in candidates
    )
    vampire_tradeoff = (
        UltimateSourceRuntimeLegalityService.assess_vampire_health_recovery_tradeoff(
            shared_non_strategic_lower_bound=(
                309.0  # level-50 base Health Recovery
                + 90.0  # Khajiit
                + 1950.0  # Elder Dragon plus Booming Voice
                + 389.606  # seven-Divines Steed
                + 811.2  # three Gold Infused Health Recovery glyphs
            ),
            incumbent_strategic_recovery=1170.0,  # 390 Ultimate, 30 per 10
            candidate_strategic_recovery=1500.0,
            vampire_health_recovery_penalty_percent=10.0,
        )
    )
    exact_counts = Counter(review.status.value for _, review in reviews)
    reviewed_increment = sum(
        review.generated_ultimate_ceiling
        for _, review in reviews
        if review.status is UltimateSourceRuntimeStatus.COMPATIBLE_INCREMENT
    )
    remaining_gap = max(0.0, 114.0 - reviewed_increment)

    print()
    print("EXACT CANONICAL RUNTIME REVIEW")
    print(
        "exact_status_counts="
        + ", ".join(f"{key}:{value}" for key, value in sorted(exact_counts.items()))
    )
    for row, review in reviews:
        print(
            f"  {row.source_id}: status={review.status.value} "
            f"generated_ultimate_ceiling={review.generated_ultimate_ceiling:.3f} "
            f"reason={review.reason}"
        )
    unresolved_statuses = {
        UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
        UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
    }
    dominated_ids = (
        {"exhilarating_drain"} if vampire_tradeoff.dominated else set()
    )
    unresolved = tuple(
        row
        for row, review in reviews
        if review.status in unresolved_statuses and row.source_id not in dominated_ids
    )
    review_by_id = {row.source_id: review for row, review in reviews}
    bounded_mutations = tuple(
        (row, review)
        for row, review in reviews
        if (
            review.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION
            and review.generated_ultimate_ceiling > 0
        )
    )

    loadout_candidates = tuple(
        UltimateSourceLoadoutCandidate(
            source_id=row.source_id,
            label=row.label,
            generated_ultimate_ceiling=review_by_id[row.source_id].generated_ultimate_ceiling,
            required_set_name=_SET_REQUIREMENTS.get(row.source_id, (None, 0))[0],
            required_set_pieces=_SET_REQUIREMENTS.get(row.source_id, (None, 0))[1],
            stochastic=row.source_id in _STOCHASTIC_SOURCE_IDS,
            action_proof_required=row.source_id in _ACTION_PROOF_SOURCE_IDS,
        )
        for row in unresolved
    )
    named_set_catalog = ExtremeNamedGearSetSlotEligibilityService(database).build()
    loadout_catalog = UltimateSourceLoadoutCombinationService.search(
        loadout_candidates,
        named_set_catalog.sets,
        required_ultimate_gap=remaining_gap,
    )

    print()
    print("VAMPIRE HEALTH RECOVERY DOMINANCE")
    print(
        "shared_non_strategic_lower_bound="
        f"{vampire_tradeoff.shared_non_strategic_lower_bound:.3f}"
    )
    print(
        "non_vampire_incumbent_lower_bound="
        f"{vampire_tradeoff.non_vampire_incumbent_lower_bound:.3f}"
    )
    print(
        "vampire_candidate_best_case="
        f"{vampire_tradeoff.vampire_candidate_best_case:.3f}"
    )
    print(
        "vampire_delta_upper_bound="
        f"{vampire_tradeoff.vampire_delta_upper_bound:.3f}"
    )
    print(f"exhilarating_drain_dominated={vampire_tradeoff.dominated}")
    print()
    print(f"bounded_mutation_candidates={len(bounded_mutations)}")
    for row, review in bounded_mutations:
        print(
            f"  mutation_ceiling: {row.source_id} "
            f"generated_ultimate_ceiling={review.generated_ultimate_ceiling:.3f} "
            f"individually_closes_original_gap={review.generated_ultimate_ceiling >= 114.0}"
        )
    print(f"reviewed_compatible_increment={reviewed_increment:.3f}")
    print(f"remaining_ultimate_gap={remaining_gap:.3f}")
    print(f"remaining_route_candidates={len(unresolved)}")
    print("remaining_candidate_ids=" + repr(tuple(row.source_id for row in unresolved)))

    print()
    print("ULTIMATE SOURCE LOADOUT COMBINATION SEARCH")
    print(f"raw_combinations={len(loadout_catalog.combinations)}")
    print(f"legal_combinations={len(loadout_catalog.legal_combinations)}")
    print(f"rejected_combinations={len(loadout_catalog.rejected_combinations)}")
    print(f"gap_closing_combinations={len(loadout_catalog.gap_closing_combinations)}")
    print(
        "minimal_gap_closing_combinations="
        f"{len(loadout_catalog.minimal_gap_closing_combinations)}"
    )
    for row in loadout_catalog.minimal_gap_closing_combinations:
        print(
            "  minimal_closer: "
            f"sources={row.source_ids!r} "
            f"ultimate_ceiling={row.total_ultimate_ceiling:.3f} "
            f"set_units={row.required_set_units} "
            f"stochastic={row.stochastic} "
            f"action_proof_required={row.action_proof_required} "
            f"runtime_proven={row.runtime_proven}"
        )
    for unresolved_reason in loadout_catalog.unresolved:
        print(f"  unresolved={unresolved_reason}")

    print("ultimate_source_denominator_discovered=True")
    print("ultimate_source_exact_review_applied=True")
    print(
        "physical_set_slot_denominator_proven="
        f"{loadout_catalog.physical_set_slot_denominator_proven}"
    )
    print("armor_weight_legality_pending=True")
    print("whole_build_health_recovery_scoring_pending=True")
    print("ultimate_source_numeric_legality_proven=False")
    print(
        "NEXT_STEP=prove seven-Heavy compatibility for surviving exact named-set "
        "witnesses, then score their whole-build Health Recovery tradeoffs"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
