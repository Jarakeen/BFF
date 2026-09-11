import pytest

from minmax.base_character_state import BaseCharacterCalculator
from minmax.combat_state import CombatState, EMPEROR_STATE_MARKER_PREFIX
from minmax.emperor_passive_input_resolver import EmperorPassiveInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs


def _state(result: GearCalculationInputs):
    return BaseCharacterCalculator().calculate(
        health=result.health,
        magicka=result.magicka,
        stamina=result.stamina,
    )


def test_emperor_passive_is_inactive_outside_home_campaign():
    base = GearCalculationInputs()
    result = EmperorPassiveInputResolver.apply(
        base,
        combat_state=CombatState(is_emperor=True, in_home_campaign=False, emperor_home_keeps=6),
    )
    assert result == base


def test_emperor_passive_applies_six_keep_ceiling_to_all_max_resources():
    result = EmperorPassiveInputResolver.apply(
        GearCalculationInputs(),
        combat_state=CombatState(is_emperor=True, in_home_campaign=True, emperor_home_keeps=6),
    )
    state = _state(result)

    assert EmperorPassiveInputResolver.percent_for_state(
        CombatState(is_emperor=True, in_home_campaign=True, emperor_home_keeps=6)
    ) == pytest.approx(0.75)
    assert state.max_health == 28_000
    assert state.max_magicka == 21_000
    assert state.max_stamina == 21_000
    assert result.applied_effect_count == 3


def test_emperor_home_keep_table_matches_reviewed_u50_tiers():
    expected = {0: 0.38, 1: 0.38, 2: 0.45, 3: 0.53, 4: 0.60, 5: 0.68, 6: 0.75}
    for keeps, percent in expected.items():
        state = CombatState(is_emperor=True, in_home_campaign=True, emperor_home_keeps=keeps)
        assert EmperorPassiveInputResolver.percent_for_state(state) == pytest.approx(percent)


def test_snapshot_marker_is_consumed_into_explicit_emperor_state():
    state = CombatState(active_buffs=(f"{EMPEROR_STATE_MARKER_PREFIX}6", "Major Resolve"))
    assert state.is_emperor is True
    assert state.in_home_campaign is True
    assert state.emperor_home_keeps == 6
    assert state.active_buffs == ("Major Resolve",)


def test_emperor_state_rejects_invalid_keep_count_and_conflicting_marker():
    with pytest.raises(ValueError, match="between 0 and 6"):
        CombatState(is_emperor=True, in_home_campaign=True, emperor_home_keeps=7)

    with pytest.raises(ValueError, match="cannot be combined"):
        CombatState(
            active_buffs=(f"{EMPEROR_STATE_MARKER_PREFIX}6",),
            is_emperor=True,
            in_home_campaign=True,
        )
