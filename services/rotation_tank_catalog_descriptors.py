from __future__ import annotations

"""Explicit Tank rotation service catalog descriptors.

Metadata only. Runtime code continues to use typed imports and explicit dependency
wiring; the catalog remains a discovery index rather than a service locator.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


ROTATION_TANK_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.tank.taunt_application_obligation",
        domain="rotation",
        purpose=(
            "Assess an explicit tank taunt-application obligation against canonical "
            "skill-component TAUNT utility evidence and the exact scheduled rotation plan."
        ),
        implementation_path="services.rotation_tank_taunt_obligation_service",
        inputs=(
            "RotationPlan",
            "RotationTankTauntApplicationRequirement",
            "SkillCoefficientRepository",
            "SkillComponentUtilityEffectRepository",
        ),
        outputs=("RotationTankTauntApplicationAssessment",),
        responsibilities=("rotation_tank_taunt_application_hard_obligation",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "The requirement must explicitly supply source skill, timing window, minimum "
            "application count, and optional bar. Canonical TAUNT utility proves only that "
            "the scheduled skill applies taunt. It does not prove taunt duration, continuous "
            "uptime, target ownership, immunity/overtaunt behavior, or survivability."
        ),
    ),
)


__all__ = ["ROTATION_TANK_SERVICE_DESCRIPTORS"]
