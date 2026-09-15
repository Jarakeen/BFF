from __future__ import annotations

"""Service-catalog descriptors for Extreme MOST Actual Heal search proof."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


EXTREME_ACTUAL_HEAL_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.actual_heal_attribute_projection",
        domain="extreme",
        purpose=(
            "Proof-reduce the complete legal 64-point Health/Magicka/Stamina simplex "
            "to the two pure resource endpoints for reviewed standing type-8 MOST Actual Heal."
        ),
        implementation_path="services.extreme_actual_heal_attribute_projection_service",
        inputs=("PlayerBuild", "HealingEntityId", "ExtremeGlobalSearchUniverse"),
        outputs=("ExtremeActualHealAttributeProjectionResult",),
        responsibilities=("extreme_actual_heal_attribute_denominator_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        roles=("Healer",),
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "The complete 2,145-allocation simplex remains the denominator. Projection "
            "fails closed for active coefficient families outside the reviewed type-8 "
            "highest-resource contract."
        ),
    ),
)


__all__ = ["EXTREME_ACTUAL_HEAL_SERVICE_DESCRIPTORS"]
