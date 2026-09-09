from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import SkillEffectKind
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_healing_event_service import ExtremeHealingEventService


class _FakeComponents:
    def get_for_skill_rank(self, _skill_rank_id):
        return (
            SimpleNamespace(coefficient_number=1, effect_kind=SkillEffectKind.HEAL, can_crit=True),
            SimpleNamespace(coefficient_number=2, effect_kind=SkillEffectKind.HEAL, can_crit=True),
        )


class _FakeTooltipService:
    components = _FakeComponents()

    def evaluate_entity_id(self, **_kwargs):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=42, name="Blood of the Elder Dragon"),
            components=(
                SimpleNamespace(coefficient_number=1, final_value=3000.0),
                SimpleNamespace(coefficient_number=2, final_value=2000.0),
            ),
            component_actual_effect_trace=(),
            unresolved=(),
        )


class _SelectingRecipientScope:
    def resolve(self, **kwargs):
        assert kwargs["ability_name"] == "Blood of the Elder Dragon"
        assert kwargs["heal_coefficient_numbers"] == (1, 2)
        assert tuple(trace.coefficient_number for trace in kwargs["coefficient_traces"]) == (1, 2)
        return SimpleNamespace(
            single_recipient_safe=True,
            recipient_selection_required=False,
            selected_coefficient_numbers=(1,),
            unresolved=(),
        )


def test_healing_event_uses_only_proven_recipient_components():
    service = ExtremeHealingEventService(
        tooltip_service=_FakeTooltipService(),
        recipient_scope=_SelectingRecipientScope(),
    )
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.20)}
        ),
        progression=None,
        active_bar="front",
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Dragon Blood proof"),
        context=context,
        entity_id="blood_of_the_elder_dragon",
    )

    assert result.heal_coefficient_numbers == (1,)
    assert result.normal_heal == pytest.approx(3000.0)
    assert result.critical_heal == pytest.approx(5100.0)
    assert result.unresolved == ()
