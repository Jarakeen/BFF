from minmax.gear_sets import GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_resource_conditioned_context_factory import (
    _ExtremeConditionedGearEffectResolver,
)


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Titanborn Strength"
    return build


def _bonus() -> GearSetBonus:
    return GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Adds 110 Weapon and Spell Damage and 1240 Offensive Penetration. "
            "While in combat, this bonus doubles when you are under 75% Health and "
            "quadruples when you are under 50% Health."
        ),
    )


def test_titanborn_requires_five_pieces_for_below_half_threshold_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION not in inactive.condition_context
    assert TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION in active.condition_context
    assert any("quadrupled five-piece power branch" in item for item in active.evidence)


def test_titanborn_conditioned_resolver_uses_quadrupled_five_piece_power() -> None:
    effects = _ExtremeConditionedGearEffectResolver().resolve(_bonus())

    assert len(effects) == 2
    assert {effect.value for effect in effects} == {440.0}
    assert {effect.condition for effect in effects} == {
        TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION
    }


def test_titanborn_exact_h1_blocker_is_reviewed_by_threshold_state() -> None:
    blocker = (
        "Titanborn Strength (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Adds 110 Weapon and Spell Damage and 1240 Offensive Penetration. "
        "While in combat, this bonus doubles when you are under 75% Health and quadruples "
        "when you are under 50% Health."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Titanborn Strength",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=129.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
