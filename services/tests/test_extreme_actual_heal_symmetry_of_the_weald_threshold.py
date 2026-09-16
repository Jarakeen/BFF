from minmax.gear_set_healing_condition_resolver import GearSetHealingConditionResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    SYMMETRY_OF_THE_WEALD_LOW_HEALTH_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Symmetry of the Weald"
    return build


def test_symmetry_requires_five_pieces_for_low_health_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert SYMMETRY_OF_THE_WEALD_LOW_HEALTH_CONDITION not in inactive.condition_context
    assert SYMMETRY_OF_THE_WEALD_LOW_HEALTH_CONDITION in active.condition_context
    assert any("10% Healing Done" in item for item in active.evidence)


def test_symmetry_exact_tooltip_maps_conditional_healing_done() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Adds 200% Status Effect Chance while your Health is above 50%. "
            "Adds 10% Healing Done while your Health is 50% or less."
        ),
    )

    effects = GearSetHealingConditionResolver().resolve(bonus)

    assert len(effects) == 1
    effect = effects[0]
    assert effect.stat is StatId.HEALING_DONE
    assert effect.value == 10.0
    assert effect.condition == SYMMETRY_OF_THE_WEALD_LOW_HEALTH_CONDITION


def test_symmetry_condition_blocker_is_reviewed_by_threshold_witness() -> None:
    blocker = (
        "Symmetry of the Weald (5): relevant set effect requires condition "
        "wearer_health_at_or_below_50_percent"
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Symmetry of the Weald",
        category="Test",
        equipped_piece_count=5,
        objective_key="healing_done",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
