from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    WARRIORS_FURY_FULL_STACKS_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Warrior's Fury"
    return build


def test_warriors_fury_requires_five_pieces_for_full_stack_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert WARRIORS_FURY_FULL_STACKS_CONDITION not in inactive.condition_context
    assert WARRIORS_FURY_FULL_STACKS_CONDITION in active.condition_context
    assert any("20 damage events" in item for item in active.evidence)
    assert any("10-second" in item for item in active.evidence)


def test_warriors_fury_maps_full_stack_power_ceiling() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) When you take damage, your Weapon and Spell Damage is increased by 24 "
            "for 5 seconds, stacking up to 20 times. This effect can occur once every half "
            "second. Upon reaching 20 stacks, the duration is doubled but can no longer be "
            "refreshed."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {480.0}
    assert {effect.condition for effect in effects} == {WARRIORS_FURY_FULL_STACKS_CONDITION}


def test_warriors_fury_h1_blocker_is_reviewed_by_full_stack_damage_witness() -> None:
    blocker = (
        "Warrior's Fury (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you take damage, your Weapon and Spell Damage is increased by 24 for "
        "5 seconds, stacking up to 20 times. This effect can occur once every half second. "
        "Upon reaching 20 stacks, the duration is doubled but can no longer be refreshed."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Warrior's Fury",
        category="Test",
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
