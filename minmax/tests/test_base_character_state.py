from minmax.base_character_state import (
    BASE_HEALTH_RECOVERY,
    BASE_MAX_HEALTH,
    BASE_MAX_MAGICKA,
    BASE_MAX_STAMINA,
    BaseCharacterCalculator,
    ResourceInputs,
)
from minmax.character_progression import AttributeAllocation
from minmax.stat_ids import StatId


def test_level_50_baseline_resources_and_recovery():
    state = BaseCharacterCalculator().calculate()

    assert state.max_health == int(BASE_MAX_HEALTH)
    assert state.max_magicka == int(BASE_MAX_MAGICKA)
    assert state.max_stamina == int(BASE_MAX_STAMINA)
    assert state.health_recovery == int(BASE_HEALTH_RECOVERY)
    assert state.magicka_recovery == 514
    assert state.stamina_recovery == 514


def test_attribute_points_use_health_122_and_magicka_stamina_111():
    calculator = BaseCharacterCalculator()

    assert calculator.max_health(ResourceInputs(attribute_points=64)).final_value == 23808
    assert calculator.max_magicka(ResourceInputs(attribute_points=64)).final_value == 19104
    assert calculator.max_stamina(ResourceInputs(attribute_points=64)).final_value == 19104


def test_calculate_uses_one_shared_attribute_pool():
    state = BaseCharacterCalculator().calculate(
        attributes=AttributeAllocation(health=20, magicka=22, stamina=22)
    )

    assert state.max_health == 18440
    assert state.max_magicka == 14442
    assert state.max_stamina == 14442


def test_flat_and_percentage_contributions_are_traced():
    trace = BaseCharacterCalculator().max_magicka(
        ResourceInputs(
            attribute_points=64,
            item_flat=100,
            set_flat=200,
            food_flat=300,
            mundus_flat=400,
            skill_flat=500,
            other_flat=600,
            skill_percent=0.05,
            buff_percent=0.10,
        )
    )

    assert trace.final_value == 24385
    assert [step.label for step in trace.steps] == [
        "base",
        "attribute points",
        "item flat",
        "set flat",
        "food flat",
        "mundus flat",
        "skill flat",
        "other flat",
        "percentage modifiers",
        "ESO rounding",
    ]


def test_race_contributions_are_named_in_the_trace():
    state = BaseCharacterCalculator().calculate(
        attributes=AttributeAllocation(magicka=64),
        race_stats={"max_magicka": 2000, "magicka_recovery": 130},
    )

    assert state.max_magicka == 21104
    assert state.magicka_recovery == 644
    assert "race" in [step.label for step in state.traces[StatId.MAX_MAGICKA].steps]
    assert "race" in [step.label for step in state.traces[StatId.MAGICKA_RECOVERY].steps]


def test_eso_rounding_uses_ceiling():
    assert BaseCharacterCalculator.eso_round(100.0) == 100
    assert BaseCharacterCalculator.eso_round(100.0001) == 101
    assert BaseCharacterCalculator.eso_round(100.9999) == 101


def test_traces_are_keyed_by_stat_id():
    state = BaseCharacterCalculator().calculate()

    assert StatId.MAX_HEALTH in state.traces
    assert StatId.MAX_MAGICKA in state.traces
    assert StatId.MAX_STAMINA in state.traces
    assert StatId.HEALTH_RECOVERY in state.traces
    assert StatId.MAGICKA_RECOVERY in state.traces
    assert StatId.STAMINA_RECOVERY in state.traces
