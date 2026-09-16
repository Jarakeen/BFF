from minmax.gear_sets import GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION,
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _build(piece_count: int = 5) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Pearlescent Ward"
    return build


def test_pearlescent_ward_requires_five_pieces_for_full_group_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION not in inactive.condition_context
    assert PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION in active.condition_context
    assert any("12-player group" in item for item in active.evidence)


def test_pearlescent_ward_exact_tooltip_maps_maximum_full_group_power() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=1,
        piece_count=5,
        description=(
            "(5 items) Grants you and up to 11 other group members Pearlescent Ward. "
            "This bonus persists through death. Pearlescent Ward increases Weapon and Spell "
            "Damage by up to 180 based on the number of group members that are alive. "
            "Current 180 Weapon and Spell Damage. Pearlescent Ward increases damage reduction "
            "from non-player enemies out of 66% based on the number of group members that are dead."
        ),
    )

    effects = ExtremeActualHealGearPreconditionEffectResolver().resolve(bonus)

    assert len(effects) == 2
    assert {effect.value for effect in effects} == {180.0}
    assert {effect.condition for effect in effects} == {
        PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION
    }


def test_pearlescent_ward_exact_h1_blocker_is_reviewed_by_group_state() -> None:
    blocker = (
        "Pearlescent Ward (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Grants you and up to 11 other group members Pearlescent Ward. "
        "This bonus persists through death. Pearlescent Ward increases Weapon and Spell Damage "
        "by up to 180 based on the number of group members that are alive. Current 180 Weapon and "
        "Spell Damage. Pearlescent Ward increases damage reduction from non-player enemies out of "
        "66% based on the number of group members that are dead."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Pearlescent Ward",
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
