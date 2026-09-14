from __future__ import annotations

"""Audit the surviving Baron Zaudrus + Decisive Ultimate-refill route.

The special named-gear frontier is closed before this audit. This slice owns the
remaining numeric/runtime boundary only: derive Decisive proc opportunities from
reviewed Ultimate-generation events, prove Baron's canonical cooldown ceiling, and
reduce the 110-Ultimate post-Blessing gap to explicit stochastic/action obligations.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.ultimate_generation_sources import (
    CombatAttackUltimateGenerationSource,
    HeroismTier,
    HeroismUltimateGenerationSource,
    HeroismWindow,
)
from services.ultimate_source_runtime_legality_service import (
    UltimateSourceRuntimeLegalityService,
    UltimateSourceRuntimeStatus,
)


SCORE_SECONDS = 24.999
POST_BLESSING_GAP = 110.0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _decisive_records(database: Path) -> tuple[str, ...]:
    if not database.is_file():
        return ()
    with sqlite3.connect(database) as db:
        columns = _columns(db, "weapon_trait_effect")
        required = {
            "material_name",
            "effect_type",
            "value",
            "secondary_value",
            "unit",
            "description",
        }
        if not required.issubset(columns):
            return ()
        rows = db.execute(
            """
            SELECT material_name, effect_type, value, secondary_value, unit,
                   COALESCE(description, '')
            FROM weapon_trait_effect
            WHERE effect_type = 'ultimate_gain_chance'
            ORDER BY id
            """
        ).fetchall()
    return tuple(
        f"weapon_trait material={material!r} effect_type={effect_type!r} "
        f"value={value!r} secondary_value={secondary!r} unit={unit!r} "
        f"description={description!r}"
        for material, effect_type, value, secondary, unit, description in rows
    )


def _baron_records(database: Path) -> tuple[str, ...]:
    if not database.is_file():
        return ()
    with sqlite3.connect(database) as db:
        gear_columns = _columns(db, "gear_set")
        bonus_columns = _columns(db, "gear_set_bonus")
        if not {"id", "name"}.issubset(gear_columns):
            return ()
        if not {"set_id", "piece_count", "description"}.issubset(bonus_columns):
            return ()
        rows = db.execute(
            """
            SELECT gs.name, gsb.piece_count, COALESCE(gsb.description, '')
            FROM gear_set gs
            JOIN gear_set_bonus gsb ON gsb.set_id = gs.id
            WHERE LOWER(COALESCE(gs.name, '')) = LOWER('Baron Zaudrus')
            ORDER BY gsb.piece_count, gsb.id
            """
        ).fetchall()
    return tuple(
        f"gear name={name!r} pieces={pieces} description={description!r}"
        for name, pieces, description in rows
    )


def _generation_events():
    base = CombatAttackUltimateGenerationSource().events(
        attack_times=tuple(float(second) for second in range(25)),
        duration_seconds=SCORE_SECONDS,
    )
    heroism = HeroismUltimateGenerationSource().events(
        windows=(
            HeroismWindow(HeroismTier.MINOR, 0.0, SCORE_SECONDS, source="Minor Heroism"),
            HeroismWindow(HeroismTier.MAJOR, 0.0, SCORE_SECONDS, source="Major Heroism"),
        ),
        duration_seconds=SCORE_SECONDS,
    )
    return base, heroism


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    decisive_records = _decisive_records(database)
    baron_records = _baron_records(database)
    base_events, heroism_events = _generation_events()
    all_events = tuple((*base_events, *heroism_events))

    decisive = UltimateSourceRuntimeLegalityService.decisive_opportunities_from_generation_events(
        all_events,
        score_seconds=SCORE_SECONDS,
    )
    opportunity_times = tuple(
        [event.time_seconds for event in base_events]
        + sorted({event.time_seconds for event in heroism_events})
    )
    decisive_review = UltimateSourceRuntimeLegalityService.review(
        "decisive",
        canonical_records=decisive_records,
        required_additional_ultimate=POST_BLESSING_GAP,
        score_seconds=SCORE_SECONDS,
        trigger_seconds=opportunity_times,
    )

    baron_trigger_seconds = tuple(float(value) for value in range(1, 25))
    baron_review = UltimateSourceRuntimeLegalityService.review(
        "baron_zaudrus",
        canonical_records=baron_records,
        required_additional_ultimate=POST_BLESSING_GAP,
        score_seconds=SCORE_SECONDS,
        trigger_seconds=baron_trigger_seconds,
    )
    requirement = UltimateSourceRuntimeLegalityService.baron_zaudrus_requirement_after_decisive(
        required_ultimate_gap=POST_BLESSING_GAP,
        decisive_all_procs_ceiling=decisive.all_procs_ultimate_ceiling,
        score_window_seconds=SCORE_SECONDS,
    )

    max_baron_procs = int(baron_review.generated_ultimate_ceiling // 4.0)
    minimum_decisive_successes_with_max_baron = max(
        0,
        int(POST_BLESSING_GAP - float(max_baron_procs) * 4.0 + 0.999999999),
    )
    expected_value_total_with_max_baron = (
        decisive.expected_extra_ultimate + baron_review.generated_ultimate_ceiling
    )
    expected_value_closes_gap = expected_value_total_with_max_baron >= POST_BLESSING_GAP - 1e-9

    print("EXTREME HEALTH RECOVERY BARON + DECISIVE RUNTIME AUDIT")
    print(f"database={database}")
    print(f"score_seconds={SCORE_SECONDS:.3f}")
    print("reviewed_blessing_peak_increment=4.000")
    print(f"post_blessing_gap={POST_BLESSING_GAP:.3f}")
    print()

    print("DECISIVE OPPORTUNITY PROOF")
    print(f"canonical_records={len(decisive_records)}")
    print(f"base_generation_events={len(base_events)}")
    print(f"heroism_generation_events={len(heroism_events)}")
    print(f"heroism_merged_opportunities={decisive.merged_heroism_opportunities}")
    print(f"non_heroism_opportunities={decisive.non_heroism_opportunities}")
    print(f"total_decisive_opportunities={decisive.total_opportunities}")
    print(f"decisive_proc_chance_percent={decisive.proc_chance_percent:.3f}")
    print(f"decisive_all_procs_ceiling={decisive.all_procs_ultimate_ceiling:.3f}")
    print(f"decisive_expected_extra_ultimate={decisive.expected_extra_ultimate:.3f}")
    print(f"decisive_review_status={decisive_review.status.value}")
    print("decisive_all_procs_is_stochastic_ceiling=True")
    print("decisive_deterministic_generation_proven=False")
    print()

    print("BARON ZAUDRUS REQUIREMENT")
    print(f"canonical_records={len(baron_records)}")
    print(f"baron_cooldown_window_ceiling={baron_review.generated_ultimate_ceiling:.3f}")
    print(f"baron_max_procs_by_reviewed_cooldown={max_baron_procs}")
    print(f"residual_gap_after_all_decisive_procs={requirement.residual_gap_after_decisive:.3f}")
    print(f"minimum_baron_procs_at_all_decisive_procs={requirement.minimum_baron_procs}")
    print(f"minimum_status_applications_at_all_decisive_procs={requirement.minimum_status_applications}")
    print(
        "minimum_average_status_applications_per_second_at_all_decisive_procs="
        f"{requirement.minimum_average_status_applications_per_second:.3f}"
    )
    print(f"combined_all_procs_ceiling={requirement.combined_ultimate_ceiling:.3f}")
    print(f"combined_all_procs_surplus={requirement.surplus_over_gap:.3f}")
    print()

    print("STOCHASTIC / ACTION BOUNDARY")
    print(
        "minimum_decisive_successes_with_max_baron_cooldown_ceiling="
        f"{minimum_decisive_successes_with_max_baron}"
    )
    print(
        "status_applications_with_max_baron_cooldown_ceiling="
        f"{max_baron_procs * 3}"
    )
    print(
        "expected_value_total_with_max_baron_cooldown_ceiling="
        f"{expected_value_total_with_max_baron:.3f}"
    )
    print(f"expected_value_closes_gap={expected_value_closes_gap}")
    print("decisive_success_probability_not_claimed=True")
    print("baron_status_application_witness_proven=False")
    print(
        "baron_cooldown_numeric_ceiling_proven="
        f"{baron_review.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION and baron_review.generated_ultimate_ceiling == 96.0}"
    )
    print(
        "decisive_numeric_opportunity_ceiling_proven="
        f"{decisive_review.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION and decisive.all_procs_ultimate_ceiling == 40.0}"
    )
    print(
        "theoretical_all_procs_gap_closes="
        f"{requirement.closes_gap_at_all_procs_ceiling}"
    )
    print("ultimate_source_numeric_legality_proven=False")
    print(
        "NEXT_STEP=construct a canonical status-effect application witness for at least 54 applications "
        "at the 40-Decisive all-procs extreme, or prove a stronger point on the Baron/Decisive tradeoff frontier"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
