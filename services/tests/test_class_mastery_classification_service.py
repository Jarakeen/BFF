from __future__ import annotations

from services.class_mastery_classification_service import (
    ClassMasteryBoundary,
    ClassMasteryClassificationService,
)
from services.class_mastery_repository import ClassMasteryPassive


def _passive(name: str, description: str) -> ClassMasteryPassive:
    return ClassMasteryPassive(
        skill_id=1,
        base_ability_id=100,
        name=name,
        class_name="Test",
        description=description,
    )


def test_standing_sheet_effect_is_classified_without_runtime_state():
    row = ClassMasteryClassificationService.classify(
        _passive(
            "Standing Power",
            "Increases your Weapon and Spell Damage by 600.",
        )
    )

    assert row.boundary is ClassMasteryBoundary.STANDING_SELF_CONTAINED
    assert row.objective_keys == ("weapon_damage", "spell_damage")


def test_target_scaled_sheet_effect_is_kept_separate_from_standing_math():
    row = ClassMasteryClassificationService.classify(
        _passive(
            "Wild Adaptation",
            "Gain 333 Weapon and Spell Damage for each status effect on your target, up to 3.",
        )
    )

    assert row.boundary is ClassMasteryBoundary.TARGET_STATE_DEPENDENT
    assert row.objective_keys == ("weapon_damage", "spell_damage")


def test_combat_triggered_sheet_effect_is_not_promoted_to_resting_math():
    row = ClassMasteryClassificationService.classify(
        _passive(
            "Triggered Health",
            "While in combat, when you cast an ability, increase your Maximum Health by 1000.",
        )
    )

    assert row.boundary is ClassMasteryBoundary.COMBAT_STATE_DEPENDENT
    assert row.objective_keys == ("max_health",)


def test_group_only_effect_cannot_raise_self_sheet_extreme():
    row = ClassMasteryClassificationService.classify(
        _passive(
            "Share It",
            "Grants group members 500 Weapon and Spell Damage.",
        )
    )

    assert row.boundary is ClassMasteryBoundary.GROUP_ONLY_OR_NON_SELF
    assert row.objective_keys == ("weapon_damage", "spell_damage")


def test_non_sheet_mastery_is_retained_without_fake_objective_score():
    row = ClassMasteryClassificationService.classify(
        _passive(
            "Utility Mastery",
            "Reduces the cost of your abilities by 5%.",
        )
    )

    assert row.boundary is ClassMasteryBoundary.NON_SHEET_OR_OTHER
    assert row.objective_keys == ()


def test_relevant_to_objective_filters_without_scoring_values():
    passives = (
        _passive("Power", "Increases your Weapon and Spell Damage by 600."),
        _passive("Health", "Increases your Maximum Health by 1000."),
    )

    rows = ClassMasteryClassificationService.relevant_to_objective(
        passives,
        "spell_damage",
    )

    assert [row.passive.name for row in rows] == ["Power"]
