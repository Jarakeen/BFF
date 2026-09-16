from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    TRACKERS_LASH_FULL_STACKS_CONDITION,
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
        build.Armor[slot]["Set"] = "Tracker's Lash"
    return build


def test_trackers_lash_requires_five_pieces_for_full_stack_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert TRACKERS_LASH_FULL_STACKS_CONDITION not in inactive.condition_context
    assert TRACKERS_LASH_FULL_STACKS_CONDITION in active.condition_context
    assert any("five outgoing attacks" in item for item in active.evidence)
    assert any("0.5" in item for item in active.evidence)
    assert any("7-second" in item for item in active.evidence)


def test_trackers_lash_maps_full_stack_power_ceiling() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) When your attack is dodged, increase your Weapon and Spell Damage by 95 "
            "for 7 seconds, stacking up to 5 times. This effect can occur once every 0.5 seconds."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {475.0}
    assert {effect.condition for effect in effects} == {TRACKERS_LASH_FULL_STACKS_CONDITION}


def test_trackers_lash_exact_h1_blocker_is_admitted() -> None:
    blocker = (
        "Tracker's Lash (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When your attack is dodged, increase your Weapon and Spell Damage by 95 for "
        "7 seconds, stacking up to 5 times. This effect can occur once every 0.5 seconds."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Tracker's Lash",
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


def test_trackers_lash_lookalike_stays_unresolved() -> None:
    blocker = (
        "Mystery Lash (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When your attack is dodged, increase your Weapon and Spell Damage by 95 for "
        "7 seconds, stacking up to 5 times. This effect can occur once every 0.5 seconds."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=2,
        set_name="Mystery Lash",
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert result.h1_mechanic_complete is False
    assert result.remaining_blockers == (blocker,)
