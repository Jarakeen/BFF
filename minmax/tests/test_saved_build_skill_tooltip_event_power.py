from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_actual_effect_modifiers import SkillComponentActualEffectModifier
from minmax.stat_ids import StatId


def test_event_power_combines_with_cp_without_leaking_into_healing_done_bucket():
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={StatId.HEALING_DONE: SimpleNamespace(final_value=0.08)}
        )
    )
    cp = SkillComponentActualEffectModifier(
        coefficient_number=1,
        power_bonus=100.0,
        additive_percent=5.0,
        sources=("CP power/healing proof",),
    )

    result = SavedBuildSkillTooltipService._combine_healing_modifiers(
        context=context,
        heal_coefficients=(1,),
        cp_modifiers=(cp,),
        additional_healing_done_percent=3.0,
        additional_healing_done_sources=("Reviewed Healing Done",),
        additional_power_bonus=1500.0,
        additional_power_sources=("Nightblade Class Mastery: An Eye for Exploitation",),
    )

    assert len(result) == 1
    modifier = result[0]
    assert modifier.coefficient_number == 1
    assert modifier.power_bonus == pytest.approx(1600.0)
    assert modifier.additive_percent == pytest.approx(16.0)
    assert modifier.sources == (
        "CP power/healing proof",
        "Nightblade Class Mastery: An Eye for Exploitation",
        "Character sheet: Healing Done",
        "Reviewed Healing Done",
    )
