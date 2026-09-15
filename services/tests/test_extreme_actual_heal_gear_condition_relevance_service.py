from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


def _row(objective: str, *blockers: str) -> ExtremeGearSetObjectiveCandidate:
    return ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Scoped Set",
        category="Test",
        equipped_piece_count=5,
        objective_key=objective,
        reviewed_delta=0.0,
        unresolved=tuple(blockers),
    )


def test_damage_type_scope_is_proven_irrelevant_to_h1_heal_power() -> None:
    row = _row(
        "spell_damage",
        "Scoped Set (5): relevant set effect requires condition ability_scope:flame_damage",
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.ignored_blockers
    assert result.remaining_blockers == ()


def test_all_reviewed_damage_type_scopes_are_h1_irrelevant() -> None:
    for scope in (
        "frost_damage",
        "shock_damage",
        "magic_damage",
        "poison_and_disease_damage",
        "physical_and_bleed_damage",
    ):
        row = _row(
            "weapon_damage",
            f"Scoped Set (5): relevant set effect requires condition ability_scope:{scope}",
        )
        assert ExtremeActualHealGearConditionRelevanceService.review(row).h1_mechanic_complete


def test_reviewed_offensive_weapon_skill_scopes_are_h1_irrelevant() -> None:
    for scope in (
        "dual_wield",
        "two_handed",
        "bow",
        "destruction_staff",
        "one_hand_and_shield",
    ):
        row = _row(
            "spell_damage",
            f"Scoped Set (5): relevant set effect requires condition ability_scope:{scope}",
        )
        result = ExtremeActualHealGearConditionRelevanceService.review(row)
        assert result.h1_mechanic_complete is True
        assert result.remaining_blockers == ()


def test_damage_only_unmapped_power_text_is_irrelevant_to_h1_heal() -> None:
    examples = (
        "Flanking Strategist (5): active set bonus is not yet mechanic-mapped: "
        "Adds 34-400 Weapon and Spell Damage to your damagingabilities when you attack an enemy from behind or their sides.",
        "Diamond's Victory (5): active set bonus is not yet mechanic-mapped: "
        "While in combat, using an ability with a range of 7 meters or less grants you Range Supremacy for 5 seconds, "
        "adding 10-437 Weapon and Spell Damage to your damage over time and ranged attacks. "
        "While in combat, using an ability with a range of over 7 meters grants you Melee Supremacy for 5 seconds, "
        "adding 10-437 Weapon and Spell Damage to your melee attacks.",
        "Oakfather's Retribution (5): active set bonus is not yet mechanic-mapped: "
        "Gain 449 Offensive Penetration against enemies for each Major Buff they have active. "
        "Gain 20 Weapon and Spell Damage against enemies for each Minor Buff they have active.",
        "Spell Strategist (5): active set bonus is not yet mechanic-mapped: "
        "When you deal damage with a Light Attack, you place a mark over your target for 5 seconds, "
        "granting you 10-460 Weapon and Spell Damage against your marked target.",
        "Elemental Succession (5): active set bonus is not yet mechanic-mapped: "
        "Whenever you deal Flame, Shock, or Frost Damage, you gain 11-492 Weapon and Spell Damage for Flame, Shock, or Frost Damage for 4 seconds.",
        "Knight-errant's Mail (5): active set bonus is not yet mechanic-mapped: "
        "Adds 10-450 Weapon and Spell Damage to your One Hand and Shield abilities. "
        "When you use a One Hand and Shield ability, you heal for 35-1537 Health.",
    )

    for blocker in examples:
        row = _row("spell_damage", blocker)
        result = ExtremeActualHealGearConditionRelevanceService.review(row)
        assert result.h1_mechanic_complete is True
        assert result.remaining_blockers == ()


def test_enemy_trigger_that_grants_global_power_stays_blocking() -> None:
    row = _row(
        "spell_damage",
        "Armor of Truth (5): active set bonus is not yet mechanic-mapped: "
        "When you deal damage to an enemy who is Off Balance, your Weapon and Spell Damage are increased by 10-460 for 10 seconds.",
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is False
    assert result.remaining_blockers


def test_standing_still_is_proven_by_standing_h1_scenario() -> None:
    row = _row(
        "spell_damage",
        "Peace and Serenity (5): relevant set effect requires condition standing_still",
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is True
    assert result.ignored_blockers
    assert result.remaining_blockers == ()


def test_class_restoration_aoe_and_other_state_conditions_remain_blocking() -> None:
    for condition in (
        "ability_scope:class",
        "ability_scope:restoration_staff",
        "ability_scope:area_of_effect",
        "moving",
    ):
        row = _row(
            "spell_damage",
            f"Scoped Set (5): relevant set effect requires condition {condition}",
        )
        result = ExtremeActualHealGearConditionRelevanceService.review(row)
        assert result.h1_mechanic_complete is False
        assert result.remaining_blockers


def test_non_power_objective_never_discards_shared_blocker() -> None:
    row = _row(
        "critical_healing",
        "Scoped Set (5): relevant set effect requires condition ability_scope:flame_damage",
    )

    result = ExtremeActualHealGearConditionRelevanceService.review(row)

    assert result.h1_mechanic_complete is False
    assert result.ignored_blockers == ()
