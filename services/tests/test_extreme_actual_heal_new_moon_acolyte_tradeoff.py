from minmax.effect_kinds import EffectKind
from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_gear_set_power_tradeoff_resolver import (
    ExtremeGearSetPowerTradeoffResolver,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


_DESCRIPTION = (
    "(5 items) Adds 9-401 Weapon and Spell Damage. "
    "Increases the cost of your active abilities by 5%."
)


def test_new_moon_acolyte_maps_only_the_h1_power_term() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=470,
        piece_count=5,
        description=_DESCRIPTION,
    )

    effects = ExtremeGearSetPowerTradeoffResolver().resolve(bonus)

    assert [
        (
            effect.stat,
            effect.operation,
            effect.value,
            effect.unit,
            effect.kind,
            effect.condition,
        )
        for effect in effects
    ] == [
        (
            StatId.WEAPON_DAMAGE,
            EffectOperation.ADD,
            401.0,
            EffectUnit.FLAT,
            EffectKind.STAT,
            None,
        ),
        (
            StatId.SPELL_DAMAGE,
            EffectOperation.ADD,
            401.0,
            EffectUnit.FLAT,
            EffectKind.STAT,
            None,
        ),
    ]


def test_new_moon_acolyte_minimum_value_is_still_versioned_by_tooltip_range() -> None:
    bonus = GearSetBonus(
        id=1,
        set_id=470,
        piece_count=5,
        description=_DESCRIPTION,
    )

    effects = ExtremeGearSetPowerTradeoffResolver().resolve(
        bonus,
        use_max_value=False,
    )

    assert {effect.value for effect in effects} == {9.0}


def test_new_moon_acolyte_exact_h1_blocker_is_reviewed_as_power_tradeoff() -> None:
    blocker = (
        "New Moon Acolyte (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Adds 9-401 Weapon and Spell Damage.  \n\n"
        "Increases the cost of your active abilities by 5%."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=470,
        set_name="New Moon Acolyte",
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


def test_new_moon_acolyte_cost_only_wording_is_not_broadly_ignored() -> None:
    blocker = (
        "Mystery Set (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Adds 9-401 Weapon and Spell Damage. "
        "Increases the cost of your active abilities by 5%."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=999,
        set_name="Mystery Set",
        category="standard",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is False
    assert result.h1_positive_modifier_proven is False
    assert result.remaining_blockers == (blocker,)
