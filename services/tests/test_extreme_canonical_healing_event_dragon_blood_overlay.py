from __future__ import annotations

from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)


class _CustomTooltipService:
    pass


def test_default_canonical_heal_service_uses_reviewed_dragon_blood_overlay(tmp_path):
    service = ExtremeCanonicalHealingEventService(
        database_path=tmp_path / "eso.db",
    )

    assert isinstance(
        service.tooltip_service.components,
        ExtremeDragonBloodSkillComponentRepository,
    )


def test_explicit_tooltip_service_is_not_replaced_by_overlay():
    tooltip = _CustomTooltipService()

    service = ExtremeCanonicalHealingEventService(
        tooltip_service=tooltip,
    )

    assert service.tooltip_service is tooltip
