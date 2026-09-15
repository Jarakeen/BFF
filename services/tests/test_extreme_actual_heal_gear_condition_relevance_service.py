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


def test_class_restoration_aoe_and_state_conditions_remain_blocking() -> None:
    for condition in (
        "ability_scope:class",
        "ability_scope:restoration_staff",
        "ability_scope:area_of_effect",
        "standing_still",
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
