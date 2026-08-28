from minmax.base_character_state import (
    BASE_HEALTH_RECOVERY,
    BASE_MAX_HEALTH,
    BASE_MAX_MAGICKA,
    BASE_MAX_STAMINA,
    BaseCharacterCalculator,
    ResourceInputs,
)
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

    assert calculator.max_health(ResourceInputs(attribute_points=64)).final_value == 237? 
