from minmax.base_character_state import BaseCharacterState
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.core_stat_calculator import CoreStatState
from minmax.derived_stats import DerivedStatTrace
from minmax.stat_ids import StatId
from services.extreme_arcanist_harnessed_quintessence_context_service import (
    ExtremeArcanistHarnessedQuintessenceContextService,
)


def _base_state() -> BaseCharacterState:
    return BaseCharacterState(
        max_health=16000,
        max_magicka=30000,
        max_stamina=12000,
        health_recovery=0,
        magicka_recovery=0,
        stamina_recovery=0,
        traces={},
    )


def _power_trace(stat: StatId) -> DerivedStatTrace:
    trace = DerivedStatTrace(stat=stat)
    trace.add("base", "set", 1000.0, 1000.0)
    trace.add("existing flat", "add", 100.0, 1100.0)
    trace.add("percentage modifiers", "multiply", 1.20, 1320.0)
    trace.add("ESO rounding", "ceil", 1320.0, 1320.0)
    trace.raw_value = 1320.0
    trace.final_value = 1320.0
    return trace


def _context() -> BuildCalculationContext:
    base = _base_state()
    return BuildCalculationContext(
        character_id="arcanist-test",
        build_id="arcanist-build",
        progression=CharacterProgression(),
        character_state=base,
        core_state=CoreStatState(
            base_character=base,
            derived={
                StatId.WEAPON_DAMAGE: _power_trace(StatId.WEAPON_DAMAGE),
                StatId.SPELL_DAMAGE: _power_trace(StatId.SPELL_DAMAGE),
            },
        ),
    )


def test_harnessed_quintessence_flat_power_is_inserted_before_percent_scaling():
    context = ExtremeArcanistHarnessedQuintessenceContextService().apply(
        _context(),
        weapon_spell_damage_bonus=284.0,
    )

    weapon = context.core_state.derived[StatId.WEAPON_DAMAGE]
    spell = context.core_state.derived[StatId.SPELL_DAMAGE]
    assert weapon.final_value == 1661.0
    assert spell.final_value == 1661.0
    assert any(step[0] == "Arcanist: Harnessed Quintessence" for step in weapon.steps)
    assert any(step[0] == "Arcanist: Harnessed Quintessence" for step in spell.steps)


def test_zero_bonus_preserves_original_context():
    original = _context()
    result = ExtremeArcanistHarnessedQuintessenceContextService().apply(
        original,
        weapon_spell_damage_bonus=0.0,
    )

    assert result is original


def test_negative_bonus_is_rejected():
    try:
        ExtremeArcanistHarnessedQuintessenceContextService().apply(
            _context(),
            weapon_spell_damage_bonus=-1.0,
        )
    except ValueError as exc:
        assert "cannot be negative" in str(exc)
    else:
        raise AssertionError("negative Harnessed Quintessence bonus should fail")
