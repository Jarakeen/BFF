from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    PELINALS_WRATH_FULL_STACKS_CONDITION,
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
        build.Armor[slot]["Set"] = "Pelinal's Wrath"
    return build


def _description() -> str:
    return (
        "(5 items) Whenever you kill an enemy you gain a damage shield that absorbs up to 3876 "
        "damage for 10 seconds and a stack of Wrath of Whitestrake for 10 seconds. Each stack "
        "of Wrath of Whitestrake grants you 100 Weapon and Spell Damage, but causes you to take "
        "160 Oblivion damage every second, up to 10 stacks. The damage shield scales off the higher "
        "of your Weapon or Spell Damage, and the damage scales off your Max Health."
    )


def test_pelinals_wrath_requires_five_pieces_for_full_stack_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert PELINALS_WRATH_FULL_STACKS_CONDITION not in inactive.condition_context
    assert PELINALS_WRATH_FULL_STACKS_CONDITION in active.condition_context
    assert any("ten enemies" in item for item in active.evidence)
    assert any("Oblivion damage" in item for item in active.evidence)


def test_pelinals_wrath_maps_ten_stack_power_ceiling_only() -> None:
    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(
        GearSetBonus(id=1, set_id=1, piece_count=5, description=_description())
    )

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {1000.0}
    assert {effect.condition for effect in effects} == {PELINALS_WRATH_FULL_STACKS_CONDITION}


def test_pelinals_wrath_exact_blocker_is_admitted_for_h1() -> None:
    blocker = (
        "Pelinal's Wrath (5): active set bonus is not yet mechanic-mapped: " + _description()
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Pelinal's Wrath",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=258.0,
        unresolved=(blocker,),
    )

    review = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert review.h1_mechanic_complete is True
    assert review.h1_positive_modifier_proven is True
    assert review.remaining_blockers == ()
    assert review.ignored_blockers == (blocker,)
