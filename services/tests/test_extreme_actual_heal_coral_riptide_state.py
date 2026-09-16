from minmax.gear_sets import GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    CORAL_RIPTIDE_MAX_POWER_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Coral Riptide"
    return build


def test_coral_riptide_requires_five_pieces_for_stamina_state_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert CORAL_RIPTIDE_MAX_POWER_CONDITION not in inactive.condition_context
    assert CORAL_RIPTIDE_MAX_POWER_CONDITION in active.condition_context
    assert any("50% current Stamina" in item for item in active.evidence)


def test_coral_riptide_exact_tooltip_maps_maximum_conditional_power() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Increases your Weapon and Spell Damage by up to 600, based on your "
            "missing Stamina, reaching the maximum at 50% Stamina.\n\n"
            "Current bonus: 0 Weapon and Spell Damage."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert len(effects) == 2
    assert {effect.value for effect in effects} == {600.0}
    assert {effect.condition for effect in effects} == {CORAL_RIPTIDE_MAX_POWER_CONDITION}


def test_coral_riptide_exact_h1_blocker_is_reviewed_by_stamina_state() -> None:
    blocker = (
        "Coral Riptide (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Increases your Weapon and Spell Damage by up to 600, based on your "
        "missing Stamina, reaching the maximum at 50% Stamina.\n\n"
        "Current bonus: 0 Weapon and Spell Damage."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=647,
        set_name="Coral Riptide",
        category="standard",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
