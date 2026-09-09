from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)


class _EmptyBaseRepository:
    def get_for_skill_rank(self, _skill_rank_id):
        return ()


class _FakeTooltipService:
    def __init__(self, *, skill_rank_id: int, skill_name: str, values: tuple[float, ...]):
        self.components = ExtremeDragonBloodSkillComponentRepository(
            "ignored.db",
            base_repository=_EmptyBaseRepository(),
        )
        self.result = SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=skill_rank_id, name=skill_name),
            components=tuple(
                SimpleNamespace(coefficient_number=index, final_value=float(value))
                for index, value in enumerate(values, start=1)
            ),
            component_actual_effect_trace=(),
            unresolved=(),
        )

    def evaluate_entity_id(self, **_kwargs):
        return self.result


class _ExplodingRecipientScope:
    def resolve(self, *, ability_name: str):
        raise AssertionError(
            f"legacy recipient guard must not run for canonical identity: {ability_name}"
        )


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


def test_elder_dragon_blood_uses_canonical_self_vs_allies_identity_not_legacy_guard():
    service = ExtremeCanonicalHealingEventService(
        tooltip_service=_FakeTooltipService(
            skill_rank_id=5399,
            skill_name="Blood of the Elder Dragon",
            values=(1000.0, 700.0),
        ),
        recipient_scope=_ExplodingRecipientScope(),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="DK", EsoClass="Dragonknight"),
        context=_context(),
        entity_id="blood_of_the_elder_dragon",
    )

    rank_id = ExtremeDragonBloodSkillComponentRepository.ELDER_DRAGON_BLOOD_RANK_ID
    assert result.heal_coefficient_numbers == (1, 2)
    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert (
        ExtremeCanonicalHealingEventService.DRAGON_BLOOD_WOUND_UNRESOLVED[rank_id]
        in result.unresolved
    )
    assert not result.mechanic_complete


def test_green_dragon_blood_still_blocks_until_periodic_total_has_tick_identity():
    service = ExtremeCanonicalHealingEventService(
        tooltip_service=_FakeTooltipService(
            skill_rank_id=5398,
            skill_name="Blood of the Green Dragon",
            values=(1000.0, 700.0),
        )
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="DK", EsoClass="Dragonknight"),
        context=_context(),
        entity_id="blood_of_the_green_dragon",
    )

    assert result.heal_coefficient_numbers == (1, 2)
    assert result.normal_heal is None
    assert result.critical_heal is None
    assert any("one-event Extreme heal is unresolved" in message for message in result.unresolved)
    assert not result.mechanic_complete
