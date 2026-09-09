from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)


class _Components:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, _skill_rank_id):
        return self.rows


class _Tooltip:
    def __init__(self, result, rows):
        self.result = result
        self.components = _Components(rows)

    def evaluate_entity_id(self, **_kwargs):
        return self.result


def _context():
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.20),
            }
        ),
        progression=None,
        active_bar="front",
    )


def test_elder_dragon_blood_keeps_lower_bound_but_blocks_unproved_wound_maximum():
    rank_id = ExtremeDragonBloodSkillComponentRepository.ELDER_DRAGON_BLOOD_RANK_ID
    rows = (
        SkillComponentClassification(
            skill_rank_id=rank_id,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            can_crit=True,
            heal_recipient_scope=HealRecipientScope.SELF,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="caster",
            heal_event_key="cast_direct",
        ),
        SkillComponentClassification(
            skill_rank_id=rank_id,
            coefficient_number=2,
            effect_kind=SkillEffectKind.HEAL,
            can_crit=True,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="nearby_allies",
            heal_event_key="cast_direct",
        ),
    )
    tooltip_result = SimpleNamespace(
        skill=SimpleNamespace(
            skill_rank_id=rank_id,
            name="Blood of the Elder Dragon",
        ),
        components=(
            SimpleNamespace(coefficient_number=1, final_value=1000.0),
            SimpleNamespace(coefficient_number=2, final_value=700.0),
        ),
        component_actual_effect_trace=(),
        unresolved=(),
    )
    service = ExtremeCanonicalHealingEventService(
        tooltip_service=_Tooltip(tooltip_result, rows)
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Elder Dragon Blood"),
        context=_context(),
        entity_id="blood_of_the_elder_dragon",
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert (
        ExtremeCanonicalHealingEventService.DRAGON_BLOOD_WOUND_UNRESOLVED[rank_id]
        in result.unresolved
    )
    assert not result.mechanic_complete
