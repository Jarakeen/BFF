from minmax.base_character_state import BaseCharacterCalculator
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.core_stat_calculator import CoreStatCalculator
from minmax.stat_ids import StatId


def test_breton_resource_racial_stats_match_reference_baseline():
    state = BaseCharacterCalculator().calculate(
        attributes=AttributeAllocation(magicka=64),
        race_stats={
            "max_magicka": 2000,
            "magicka_recovery": 130,
        },
    )

    assert state.max_health == 16000
    assert state.max_magicka == 21104
    assert state.max_stamina == 12000
    assert state.health_recovery == 309
    assert state.magicka_recovery == 644
    assert state.stamina_recovery == 514


def test_breton_spell_resistance_is_applied_as_a_race_contribution():
    base = BaseCharacterCalculator().calculate(attributes=AttributeAllocation(magicka=64))
    progression = CharacterProgression(attributes=AttributeAllocation(magicka=64))

    state = CoreStatCalculator().calculate(
        character_progression=progression,
        base_character=base,
        race_stats={"spell_resistance": 2310},
    )

    assert state.derived[StatId.SPELL_RESISTANCE].final_value == 2310
    assert state.derived[StatId.SPELL_RESISTANCE].steps[-2][0] == "race"


def test_core_stat_naked_character_bases_match_reference_sheet():
    base = BaseCharacterCalculator().calculate()
    progression = CharacterProgression()
    state = CoreStatCalculator().calculate(
        character_progression=progression,
        base_character=base,
    )

    assert state.derived[StatId.WEAPON_DAMAGE].final_value == 1000
    assert state.derived[StatId.SPELL_DAMAGE].final_value == 1000
    assert state.derived[StatId.WEAPON_CRITICAL].final_value == 0.10
    assert state.derived[StatId.SPELL_CRITICAL].final_value == 0.10
    assert state.derived[StatId.CRITICAL_CHANCE].final_value == 0.10
    assert state.derived[StatId.CRITICAL_DAMAGE].final_value == 0.50
    assert state.derived[StatId.CRITICAL_HEALING].final_value == 0.0
    assert state.derived[StatId.CRITICAL_RESISTANCE].final_value == 1320
    assert state.derived[StatId.PHYSICAL_RESISTANCE].final_value == 0
    assert state.derived[StatId.SPELL_RESISTANCE].final_value == 0
    assert state.derived[StatId.PHYSICAL_PENETRATION].final_value == 0
    assert state.derived[StatId.SPELL_PENETRATION].final_value == 0
