from __future__ import annotations

"""Read-only H1 objective and distant-heal witness audit for Blind Path Induction."""

from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from minmax.gear_set_repository import GearSetRepository
from minmax.skill_component_classification import SkillEffectKind
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidateService


DISTANCE_THRESHOLD = 15.0


def _value(raw: object) -> str:
    return str(getattr(raw, "value", raw))


def _distant_heal_witnesses(database: Path) -> tuple[tuple[object, ...], ...]:
    candidate_service = ExtremeHealSkillCandidateService(database)
    rows = candidate_service._skill_rows()
    range_by_rank: dict[int, tuple[float, float | None]] = {}
    with sqlite3.connect(database) as connection:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(skill_rank)").fetchall()
        }
        if not {"id", "min_range", "max_range"}.issubset(columns):
            return ()
        for rank_id, minimum, maximum in connection.execute(
            "SELECT id, min_range, max_range FROM skill_rank"
        ).fetchall():
            try:
                minimum_value = float(minimum or 0.0)
                maximum_value = float(maximum) if maximum is not None else None
            except (TypeError, ValueError):
                continue
            range_by_rank[int(rank_id)] = (minimum_value, maximum_value)

    witnesses: list[tuple[object, ...]] = []
    seen: set[tuple[int, int]] = set()
    for row in rows:
        identity = (int(row["skill_id"]), int(row["morph"]))
        if identity in seen:
            continue
        seen.add(identity)
        rank_id = int(row["skill_rank_id"])
        minimum, maximum = range_by_rank.get(rank_id, (0.0, None))
        if maximum is None or maximum <= DISTANCE_THRESHOLD:
            continue
        heals = tuple(
            component
            for component in candidate_service.components.get_for_skill_rank(rank_id)
            if component.effect_kind is SkillEffectKind.HEAL
        )
        if not heals:
            continue
        recipient_scopes = tuple(
            sorted(
                {
                    _value(component.heal_recipient_scope)
                    for component in heals
                    if component.heal_recipient_scope is not None
                }
            )
        )
        complete = all(component.is_complete_heal_event_identity for component in heals)
        witnesses.append(
            (
                str(row["name"] or ""),
                str(row["skill_line"] or ""),
                str(row["class_type"] or ""),
                rank_id,
                minimum,
                maximum,
                len(heals),
                recipient_scopes,
                complete,
            )
        )
    return tuple(
        sorted(
            witnesses,
            key=lambda item: (
                str(item[2]).casefold(),
                str(item[1]).casefold(),
                str(item[0]).casefold(),
                int(item[3]),
            ),
        )
    )


def main() -> int:
    database = get_data_dir() / "eso.db"
    repository = GearSetRepository(database)
    objective_row = ExtremeGearSetObjectiveService.candidate_for_set(
        repository,
        "Blind Path Induction",
        "healing_done",
    )
    h1_review = ExtremeActualHealGearConditionRelevanceService.review(objective_row)
    witnesses = _distant_heal_witnesses(database)

    print("EXTREME E2 H1 BLIND PATH INDUCTION OBJECTIVE AUDIT")
    print(f"database={database}")
    print(f"distance_threshold={DISTANCE_THRESHOLD!r}")
    print(f"reviewed_delta={objective_row.reviewed_delta!r}")
    print(f"source_effect_count={len(objective_row.source_effects)}")
    for bonus in objective_row.source_bonuses:
        if int(bonus.piece_count) == 5:
            print(f"five_piece_description={str(bonus.description or '')!r}")
    for effect in objective_row.source_effects:
        stat = getattr(getattr(effect, "stat", None), "value", getattr(effect, "stat", None))
        operation = getattr(
            getattr(effect, "operation", None),
            "value",
            getattr(effect, "operation", None),
        )
        unit = getattr(getattr(effect, "unit", None), "value", getattr(effect, "unit", None))
        print(
            f"effect stat={stat!r} operation={operation!r} unit={unit!r} "
            f"value={effect.value!r} condition={effect.condition!r} source={effect.source!r}"
        )
    print(f"unresolved_count={len(objective_row.unresolved)}")
    for blocker in objective_row.unresolved:
        print(f"unresolved={blocker!r}")
    print(f"h1_mechanic_complete={h1_review.h1_mechanic_complete}")
    print(f"h1_positive_modifier_proven={h1_review.h1_positive_modifier_proven}")
    for blocker in h1_review.remaining_blockers:
        print(f"h1_remaining_blocker={blocker!r}")

    print(f"distant_heal_witness_count={len(witnesses)}")
    print("DISTANT HEAL RANGE WITNESSES")
    for (
        name,
        skill_line,
        class_type,
        rank_id,
        minimum,
        maximum,
        heal_count,
        recipient_scopes,
        complete,
    ) in witnesses:
        print(
            f"  name={name!r} line={skill_line!r} class={class_type!r} "
            f"skill_rank_id={rank_id} min_range={minimum!r} max_range={maximum!r} "
            f"heal_components={heal_count} recipient_scopes={recipient_scopes!r} "
            f"complete_heal_identity={complete}"
        )
    print(
        "NEXT_STEP=admit Blind Path Induction only when the selected winning heal "
        "can legally reach and affect a target more than 15 meters away"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
