from __future__ import annotations

"""Phase 14 combat-simulation service catalog metadata."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


COMBAT_SIMULATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="simulation.outgoing_damage_bridge",
        domain="simulation",
        purpose=(
            "Bridge already-resolved canonical Rotation DD action damage evidence into "
            "explicit post-mitigation outgoing-damage records for deterministic simulation."
        ),
        implementation_path="services.combat_simulation_outgoing_damage_service",
        inputs=(
            "RotationPlan",
            "GeneratedRotationCandidate",
            "RotationActionDamageEvidenceProvider",
            "TargetIdentity",
        ),
        outputs=("CombatSimulationOutgoingDamageProjection",),
        dependencies=(),
        responsibilities=("combat_simulation_outgoing_damage_projection",),
        roles=("DD", "DPS", "Healer", "Tank"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Owns no ESO damage formula. Damage magnitude, crit, mitigation, execute, "
            "periodic/runtime, and proc semantics remain with the authoritative Rotation "
            "damage providers; missing evidence stays unresolved."
        ),
    ),
)


__all__ = ["COMBAT_SIMULATION_SERVICE_DESCRIPTORS"]
