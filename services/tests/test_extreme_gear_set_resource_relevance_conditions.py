from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.effect_kinds import EffectKind
from minmax.stat_ids import StatId
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


def _effect(stat, value, condition, operation=EffectOperation.ADD, unit=EffectUnit.FLAT):
    return Effect(
        operation=operation,
        value=value,
        source="Test Set (5)",
        stat=stat,
        kind=EffectKind.STAT,
        unit=unit,
        condition=condition,
    )


def test_known_finite_resource_conditions_are_relevant_not_unresolved():
    cases = (
        (StatId.MAX_HEALTH, "max_health", "food_buff_active"),
        (StatId.MAX_MAGICKA, "max_magicka", "drink_buff_active"),
        (StatId.MAX_MAGICKA, "max_magicka", "pet_active"),
        (StatId.MAX_STAMINA, "max_stamina", "transformed"),
        (StatId.MAX_MAGICKA, "max_magicka", "destruction_staff_equipped"),
    )
    for stat, objective, condition in cases:
        contribution, blocker = ExtremeGearSetObjectiveService._project_relevant_effect(
            _effect(stat, 1000.0, condition),
            objective,
        )
        assert contribution == 1000.0
        assert blocker is None


def test_unknown_condition_still_fails_closed():
    contribution, blocker = ExtremeGearSetObjectiveService._project_relevant_effect(
        _effect(StatId.MAX_MAGICKA, 1000.0, "mysterious_state"),
        "max_magicka",
    )
    assert contribution is None
    assert "mysterious_state" in blocker


def test_non_resource_objectives_keep_existing_conditional_blocker():
    contribution, blocker = ExtremeGearSetObjectiveService._project_relevant_effect(
        _effect(StatId.SPELL_DAMAGE, 450.0, "pet_active"),
        "spell_damage",
    )
    assert contribution is None
    assert "pet_active" in blocker


def test_percentage_max_resource_effect_remains_stacking_blocker():
    contribution, blocker = ExtremeGearSetObjectiveService._project_relevant_effect(
        _effect(
            StatId.MAX_HEALTH,
            5.0,
            "armor_ability_slotted",
            operation=EffectOperation.ADD_PERCENT,
            unit=EffectUnit.PERCENT,
        ),
        "max_health",
    )
    assert contribution is None
    assert "stacking/reference review" in blocker
