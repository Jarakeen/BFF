from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    CAMONNA_TONG_MAX_POWER_CONDITION,
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
        build.Armor[slot]["Set"] = "Camonna Tong"
    return build


def test_camonna_tong_requires_five_pieces_for_max_power_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert CAMONNA_TONG_MAX_POWER_CONDITION not in inactive.condition_context
    assert CAMONNA_TONG_MAX_POWER_CONDITION in active.condition_context
    assert any("27,000" in item for item in active.evidence)
    assert any("30 seconds" in item for item in active.evidence)


def test_camonna_tong_maps_explicit_540_power_cap() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) When you kill a monster and gain Experience Points, gain 1 Weapon and "
            "Spell Damage for every 50 Experience Points the monster is worth for 30 seconds. "
            "This bonus can stack up to a maximum of 540 Weapon and Spell Damage. This item "
            "set is not affected by Experience Point boosting effects."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert {effect.stat for effect in effects} == {StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE}
    assert {effect.value for effect in effects} == {540.0}
    assert {effect.condition for effect in effects} == {CAMONNA_TONG_MAX_POWER_CONDITION}


def test_camonna_tong_exact_h1_blocker_is_admitted_by_capped_xp_witness() -> None:
    blocker = (
        "Camonna Tong (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you kill a monster and gain Experience Points, gain 1 Weapon and Spell "
        "Damage for every 50 Experience Points the monster is worth for 30 seconds. This bonus "
        "can stack up to a maximum of 540 Weapon and Spell Damage. This item set is not affected "
        "by Experience Point boosting effects."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Camonna Tong",
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
