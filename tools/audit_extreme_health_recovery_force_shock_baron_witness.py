from __future__ import annotations

"""Prove a canonical all-procs status witness for the Baron + Decisive Extreme route.

The preceding runtime audit reduces the surviving route to 18 Baron Zaudrus procs,
therefore 54 status applications, when all 40 reviewed Decisive opportunities proc.
This diagnostic reserves four one-second action slots for the already-reviewed
Blessing-at-the-Peak Earthen Heart cadence and uses Force Shock for the remaining
18 explicit skill actions. Each Force Shock has Flame/Frost/Shock direct-damage
components, so the shared status-opportunity service exposes three stochastic status
rolls per cast. The audit proves only the theoretical all-procs ceiling, never a
reliable or expected rotation outcome.
"""

import argparse
from collections import Counter
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.status_effect_chance import StatusEffectChanceSource
from services.rotation_skill_timing_evidence_service import (
    RotationSkillTimingEvidenceService,
)
from services.skill_choice_service import load_skill_choices
from services.status_application_opportunity_service import (
    StatusApplicationOpportunityService,
)
from services.ultimate_source_runtime_legality_service import (
    UltimateSourceRuntimeLegalityService,
    UltimateSourceRuntimeStatus,
)


SCORE_SECONDS = 24.999
POST_DECISIVE_RESIDUAL_GAP = 70.0
REQUIRED_BARON_PROCS = 18
REQUIRED_STATUS_APPLICATIONS = 54
BLESSING_ACTION_TIMES = (1.0, 7.0, 13.0, 19.0)
FORCE_SHOCK_CAST_TIMES = (
    2.0, 3.0, 4.0, 5.0, 6.0,
    8.0, 9.0, 10.0, 11.0, 12.0,
    14.0, 15.0, 16.0, 17.0, 18.0,
    20.0, 21.0, 22.0,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


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


def _exact_skill_row(database: Path, name: str) -> tuple[dict | None, tuple[str, ...]]:
    rows = tuple(
        row for row in load_skill_choices(database)
        if str(row.get("name") or "").strip().casefold() == name.casefold()
    )
    if len(rows) != 1:
        return None, (f"expected one canonical {name!r} skill row, found {len(rows)}",)
    return rows[0], ()


def _max_rank_skill_row(database: Path, name: str) -> tuple[dict | None, tuple[str, ...]]:
    """Resolve the highest imported rank for one exact skill name.

    ``load_skill_choices`` deliberately exposes one representative UI row, which is
    not sufficient evidence for rank-scaled passives such as Elemental Force. This
    helper stays audit-local and reads the canonical maximum rank without changing UI
    selection semantics.
    """

    if not database.is_file():
        return None, (f"canonical skill database is unavailable: {database}",)
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        skill_columns = _columns(db, "skill")
        rank_columns = _columns(db, "skill_rank")
        ability_columns = _columns(db, "ability")
        required_skill = {"id", "name", "skill_line", "is_passive"}
        required_rank = {
            "id", "skill_id", "ability_id", "rank", "raw_name",
            "raw_description", "raw_tooltip", "raw_coef", "coef_types",
        }
        required_ability = {"ability_id", "name", "description"}
        missing = tuple(sorted(
            (required_skill - skill_columns)
            | (required_rank - rank_columns)
            | (required_ability - ability_columns)
        ))
        if missing:
            return None, ("canonical max-rank skill evidence columns missing: " + ", ".join(missing),)
        rows = db.execute(
            """
            SELECT
                sr.ability_id,
                COALESCE(NULLIF(sr.raw_name, ''), NULLIF(a.name, ''), s.name) AS name,
                COALESCE(NULLIF(sr.raw_description, ''), NULLIF(a.description, ''), '') AS description,
                COALESCE(sr.raw_tooltip, '') AS raw_tooltip,
                COALESCE(sr.raw_coef, '') AS raw_coef,
                COALESCE(sr.coef_types, '') AS coef_types,
                s.skill_line,
                s.is_passive,
                COALESCE(sr.rank, 0) AS rank
            FROM skill_rank sr
            JOIN skill s ON s.id = sr.skill_id
            LEFT JOIN ability a ON a.ability_id = sr.ability_id
            WHERE LOWER(TRIM(COALESCE(NULLIF(sr.raw_name, ''), NULLIF(a.name, ''), s.name))) = LOWER(?)
            ORDER BY COALESCE(sr.rank, 0) DESC, sr.id DESC
            """,
            (name.strip(),),
        ).fetchall()
    if not rows:
        return None, (f"expected canonical max-rank {name!r} row, found 0",)
    top_rank = int(rows[0]["rank"] or 0)
    top = tuple(row for row in rows if int(row["rank"] or 0) == top_rank)
    if len(top) != 1:
        return None, (f"expected one max-rank canonical {name!r} row at rank {top_rank}, found {len(top)}",)
    return dict(top[0]), ()


def _normalize_eso_text(value: object) -> str:
    """Remove ESO color markup so numeric tooltip evidence remains searchable."""

    text = str(value or "")
    text = re.sub(r"\|c[0-9a-fA-F]{6}", "", text)
    text = text.replace("|r", "")
    return " ".join(text.split()).casefold()


def _evidence_text(row: dict | None) -> str:
    if row is None:
        return ""
    return _normalize_eso_text(
        " ".join(
            str(row.get(key) or "")
            for key in ("name", "description", "raw_tooltip", "raw_coef", "coef_types")
        )
    )


def _contains(row: dict | None, *fragments: str) -> bool:
    text = _evidence_text(row)
    return bool(text) and all(_normalize_eso_text(fragment) in text for fragment in fragments)


def _action_schedule_proven() -> bool:
    actions = tuple(sorted((*BLESSING_ACTION_TIMES, *FORCE_SHOCK_CAST_TIMES)))
    return (
        len(actions) == len(set(actions))
        and all(0.0 < value <= SCORE_SECONDS for value in actions)
        and all(later - earlier >= 1.0 - 1e-9 for earlier, later in zip(actions, actions[1:]))
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    force_shock, force_unresolved = _exact_skill_row(database, "Force Shock")
    elemental_force, passive_unresolved = _max_rank_skill_row(database, "Elemental Force")
    force_semantics_proven = bool(
        force_shock
        and str(force_shock.get("skill_line") or "").strip().casefold() == "destruction staff"
        and not int(force_shock.get("is_passive") or 0)
        and _contains(force_shock, "flame damage", "frost damage", "shock damage")
    )
    elemental_force_proven = bool(
        elemental_force
        and str(elemental_force.get("skill_line") or "").strip().casefold() == "destruction staff"
        and int(elemental_force.get("is_passive") or 0)
        and _contains(elemental_force, "status effects", "100%")
    )

    timing = RotationSkillTimingEvidenceService(database).resolve_skill("Force Shock")
    force_timing_proven = bool(
        timing.evidence is not None
        and timing.evidence.occupancy_seconds is None
        and not timing.unresolved
    )

    status_catalog = StatusApplicationOpportunityService.from_damage_casts(
        cast_times=FORCE_SHOCK_CAST_TIMES,
        damage_types=("flame", "frost", "shock"),
        source_family=StatusEffectChanceSource.SINGLE_TARGET_DIRECT,
        increase_percent=100.0,
        source_name="Force Shock + Elemental Force",
        score_seconds=SCORE_SECONDS,
    )
    per_time = Counter(round(row.time_seconds, 9) for row in status_catalog.opportunities)
    three_per_cast = all(per_time.get(round(value, 9), 0) == 3 for value in FORCE_SHOCK_CAST_TIMES)
    baron_proc_times = tuple(
        value for value in FORCE_SHOCK_CAST_TIMES
        if per_time.get(round(value, 9), 0) >= 3
    )

    baron_records = _baron_records(database)
    baron_review = UltimateSourceRuntimeLegalityService.review(
        "baron_zaudrus",
        canonical_records=baron_records,
        required_additional_ultimate=POST_DECISIVE_RESIDUAL_GAP,
        score_seconds=SCORE_SECONDS,
        trigger_seconds=baron_proc_times,
    )

    evidence_unresolved = tuple((*force_unresolved, *passive_unresolved, *timing.unresolved))
    witness_proven = bool(
        not evidence_unresolved
        and force_semantics_proven
        and elemental_force_proven
        and force_timing_proven
        and _action_schedule_proven()
        and status_catalog.denominator_proven
        and three_per_cast
        and status_catalog.all_procs_application_ceiling >= REQUIRED_STATUS_APPLICATIONS
        and len(baron_proc_times) >= REQUIRED_BARON_PROCS
        and baron_review.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION
        and baron_review.generated_ultimate_ceiling >= POST_DECISIVE_RESIDUAL_GAP
    )

    print("EXTREME HEALTH RECOVERY FORCE SHOCK / BARON STATUS WITNESS")
    print(f"database={database}")
    print(f"score_seconds={SCORE_SECONDS:.3f}")
    print(f"force_shock_canonical_row_proven={force_semantics_proven}")
    print(f"elemental_force_100_percent_increase_proven={elemental_force_proven}")
    if elemental_force is not None:
        print(f"elemental_force_max_rank={int(elemental_force.get('rank') or 0)}")
        print(f"elemental_force_ability_id={int(elemental_force.get('ability_id') or 0)}")
        if not elemental_force_proven:
            print(f"elemental_force_normalized_evidence={_evidence_text(elemental_force)!r}")
    print(f"force_shock_canonical_instant_timing_proven={force_timing_proven}")
    if timing.evidence is not None:
        print(f"force_shock_ability_id={timing.evidence.ability_id}")
        print(f"force_shock_cast_time_seconds={timing.evidence.cast_time_seconds!r}")
        print(f"force_shock_channel_time_seconds={timing.evidence.channel_time_seconds!r}")
    for item in evidence_unresolved:
        print(f"  evidence_unresolved={item}")
    print()

    print("ACTION WITNESS")
    print(f"blessing_reserved_action_times={BLESSING_ACTION_TIMES!r}")
    print(f"force_shock_cast_times={FORCE_SHOCK_CAST_TIMES!r}")
    print(f"force_shock_cast_count={len(FORCE_SHOCK_CAST_TIMES)}")
    print(f"one_second_action_cadence_proven={_action_schedule_proven()}")
    print()

    print("STATUS OPPORTUNITY WITNESS")
    print(f"status_opportunity_denominator_proven={status_catalog.denominator_proven}")
    print(f"damage_components_per_force_shock={3 if three_per_cast else 0}")
    print(f"status_names={tuple(sorted({row.status_name for row in status_catalog.opportunities}))!r}")
    print(f"per_component_status_chance={status_catalog.opportunities[0].chance if status_catalog.opportunities else 0.0:.3f}")
    print(f"all_procs_status_application_ceiling={status_catalog.all_procs_application_ceiling}")
    print(f"expected_status_applications={status_catalog.expected_application_count:.3f}")
    print(f"deterministic_status_applications={status_catalog.deterministic_application_count}")
    print(f"all_status_procs_is_stochastic_ceiling={status_catalog.all_procs_is_stochastic}")
    for item in status_catalog.unresolved:
        print(f"  status_unresolved={item}")
    print()

    print("BARON PROC WITNESS")
    print(f"required_status_applications={REQUIRED_STATUS_APPLICATIONS}")
    print(f"baron_proc_times={baron_proc_times!r}")
    print(f"baron_proc_count={len(baron_proc_times)}")
    print(f"baron_review_status={baron_review.status.value}")
    print(f"baron_generated_ultimate_ceiling={baron_review.generated_ultimate_ceiling:.3f}")
    print(f"baron_remaining_residual_gap={baron_review.remaining_ultimate_gap:.3f}")
    print(f"baron_status_application_witness_proven={witness_proven}")
    print("baron_status_witness_is_stochastic_ceiling=True")
    print("baron_status_witness_deterministic=False")
    print()

    print(f"ultimate_source_theoretical_max_legality_proven={witness_proven}")
    print("ultimate_source_deterministic_legality_proven=False")
    if witness_proven:
        print(
            "NEXT_STEP=compose the proven stochastic Ultimate refill witness back into the "
            "whole Health Recovery score and close the final Extreme record"
        )
        return 0
    print(
        "NEXT_STEP=close the reported Force Shock/Elemental Force/timing/action evidence gap "
        "before claiming the Baron status witness"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
