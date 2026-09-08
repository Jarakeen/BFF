from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_actual_effect_modifiers import SkillComponentActualEffectModifier
from minmax.stat_ids import StatId


def test_sheet_cp_and_reviewed_extra_healing_done_share_one_additive_bucket():
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.HEALING_DONE: SimpleNamespace(final_value=0.16),
            }
        )
    )
    cp = SkillComponentActualEffectModifier(
        coefficient_number=1,
        additive_percent=8.0,
        sources=("Blessed",),
    )

    modifiers = SavedBuildSkillTooltipService._combine_healing_modifiers(
        context=context,
        heal_coefficients=(1,),
        cp_modifiers=(cp,),
        additional_healing_done_percent=12.0,
        additional_healing_done_sources=("Reviewed extra Healing Done",),
    )

    assert len(modifiers) == 1
    modifier = modifiers[0]
    assert modifier.additive_percent == pytest.approx(36.0)
    assert modifier.sources == (
        "Blessed",
        "Character sheet: Healing Done",
        "Reviewed extra Healing Done",
    )


def test_reviewed_extra_healing_done_does_not_create_power_bonus():
    context = SimpleNamespace(core_state=SimpleNamespace(derived={}))

    modifiers = SavedBuildSkillTooltipService._combine_healing_modifiers(
        context=context,
        heal_coefficients=(2,),
        cp_modifiers=(),
        additional_healing_done_percent=12.0,
        additional_healing_done_sources=("Reviewed extra Healing Done",),
    )

    assert len(modifiers) == 1
    assert modifiers[0].power_bonus == 0.0
    assert modifiers[0].additive_percent == pytest.approx(12.0)
