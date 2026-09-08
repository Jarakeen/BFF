from __future__ import annotations

from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)
from services.extreme_sorcerer_skill_component_repository import (
    ExtremeSorcererSkillComponentRepository,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


class _CustomTooltipService:
    pass


def test_default_canonical_heal_service_layers_reviewed_identity_overlays(tmp_path):
    service = ExtremeCanonicalHealingEventService(
        database_path=tmp_path / "eso.db",
    )

    healer = service.tooltip_service.components
    assert isinstance(healer, RotationHealerU50SkillComponentRepository)

    sorcerer = healer.base_repository
    assert isinstance(sorcerer, ExtremeSorcererSkillComponentRepository)
    assert isinstance(
        sorcerer.base_repository,
        ExtremeDragonBloodSkillComponentRepository,
    )


def test_explicit_tooltip_service_is_not_replaced_by_overlay():
    tooltip = _CustomTooltipService()

    service = ExtremeCanonicalHealingEventService(
        tooltip_service=tooltip,
    )

    assert service.tooltip_service is tooltip
