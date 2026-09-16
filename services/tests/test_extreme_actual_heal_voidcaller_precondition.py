from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    WARRIORS_FURY_FULL_STACKS_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Voidcaller"
    return build


def test_voidcaller_reuses_full_stack_damage_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert WARRIORS_FURY_FULL_STACKS_CONDITION not in inactive.condition_context
    assert WARRIORS_FURY_FULL_STACKS_CONDITION in active.condition_context
    assert any("Voidcaller" in item for item in active.evidence)
    assert any("20 damage events" in item for item in active.evidence)


def test_voidcaller_identical_five_piece_maps_to_480_power() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) When you take damage, your Weapon and Spell Damage is increased by 24 "
            "for 5 seconds, stacking up to 20 times. This effect can occur once every half "
            "second. Upon reaching 20 stacks, the duration is doubled but can no longer be refreshed."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {480.0}
    assert {effect.condition for effect in effects} == {WARRIORS_FURY_FULL_STACKS_CONDITION}


def test_voidcaller_exact_blocker_is_admitted_by_reviewed_full_stack_witness() -> None:
    blocker = (
        "Voidcaller (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you take damage, your Weapon and Spell Damage is increased by 24 for "
        "5 seconds, stacking up to 20 times. This effect can occur once every half second. "
        "Upon reaching 20 stacks, the duration is doubled but can no longer be refreshed."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Voidcaller",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert result.h1_mechanic_complete is True
    assert result.h1_positive_modifier_proven is True
    assert result.remaining_blockers == ()
    assert result.ignored_blockers == (blocker,)
