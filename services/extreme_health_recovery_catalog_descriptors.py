from __future__ import annotations

"""Service-catalog descriptors for Extreme Health Recovery proof slices."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


EXTREME_HEALTH_RECOVERY_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.named_gear_armor_weight_realization",
        domain="extreme",
        purpose=(
            "Prove an exact named-set physical witness under an explicit canonical "
            "armor-weight requirement."
        ),
        implementation_path=(
            "services.extreme_named_gear_armor_weight_realization_service"
        ),
        inputs=(
            "ExtremeGearSetCountTopology",
            "ExtremeNamedGearSetSlotEligibility",
            "CanonicalEsoDatabase",
            "RequiredArmorWeight",
        ),
        outputs=("ExtremeNamedGearArmorWeightRealizationResult",),
        responsibilities=("extreme_named_gear_armor_weight_realization",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Named-set armor pieces must support the requested weight; jewelry, "
            "weapons, and unassigned ordinary armor remain distinct physical slots."
        ),
    ),
)


__all__ = ["EXTREME_HEALTH_RECOVERY_SERVICE_DESCRIPTORS"]
