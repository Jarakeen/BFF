from minmax.gear_set_healing_condition_resolver import GearSetHealingConditionResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    SENCHES_BITE_DODGE_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Senche's Bite"
    return build


def test_senches_bite_requires_five_pieces_for_dodge_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert SENCHES_BITE_DODGE_CONDITION not in inactive.condition_context
    assert SENCHES_BITE_DODGE_CONDITION in active.condition_context
    assert any("successfully Dodge" in item for item in active.evidence)


def test_senches_bite_canonical_tooltip_maps_maximum_conditional_critical_healing() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Whenever you successfully Dodge, increase your Critical Damage and "
            "Critical Healing by |cffffff0-15|r% for |cffffff10|r seconds."
        ),
    )

    effects = GearSetHealingConditionResolver().resolve(bonus)

    assert len(effects) == 2
    by_stat = {effect.stat: effect for effect in effects}
    assert by_stat[StatId.CRITICAL_HEALING].value == 15.0
    assert by_stat[StatId.CRITICAL_HEALING].condition == SENCHES_BITE_DODGE_CONDITION
    assert by_stat[StatId.CRITICAL_DAMAGE].value == 15.0
    assert by_stat[StatId.CRITICAL_DAMAGE].condition == SENCHES_BITE_DODGE_CONDITION


def test_senches_bite_canonical_tooltip_preserves_minimum_when_requested() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Whenever you successfully Dodge, increase your Critical Damage and "
            "Critical Healing by 0-15% for 10 seconds."
        ),
    )

    effects = GearSetHealingConditionResolver().resolve(bonus, use_max_value=False)

    assert {effect.value for effect in effects} == {0.0}


def _review(blocker: str):
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Senche's Bite",
        category="Test",
        equipped_piece_count=5,
        objective_key="critical_healing",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )
    return ExtremeActualHealGearConditionRelevanceService.review(row)


def test_senches_bite_exact_h1_blocker_is_reviewed_by_dodge_witness() -> None:
    blocker = (
        "Senche's Bite (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Whenever you successfully Dodge, increase your Critical Damage and "
        "Critical Healing by 0-15% for 10 seconds."
    )

    result = _review(blocker)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)


def test_senches_bite_resolved_condition_blocker_is_reviewed_by_dodge_witness() -> None:
    blocker = "Senche's Bite (5): relevant set effect requires condition successful_dodge_recent"

    result = _review(blocker)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
