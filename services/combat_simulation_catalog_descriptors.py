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
    ServiceDescriptor(
        service_id="simulation.sequential_dd_health_feedback",
        domain="simulation",
        purpose=(
            "Evaluate canonical DD actions in exact schedule order while feeding the "
            "simulated target Health created by earlier actions back into later "
            "target-Health-sensitive damage evaluation."
        ),
        implementation_path=(
            "services.combat_simulation_sequential_dd_damage_service"
        ),
        inputs=(
            "RotationPlan",
            "GeneratedRotationCandidate",
            "RotationActionDamageEvidenceProvider",
            "CombatSimulationTargetState",
            "TargetIdentity",
        ),
        outputs=("CombatSimulationSequentialDamageProjection",),
        dependencies=("simulation.outgoing_damage_bridge",),
        responsibilities=("combat_simulation_sequential_target_health_feedback",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Owns only target Health progression between already-resolved actions. "
            "Execute thresholds, amplification, skill formulas, mitigation, and "
            "target-state mechanics remain with existing canonical Rotation services."
        ),
    ),
    ServiceDescriptor(
        service_id="simulation.saved_build_dd_provider",
        domain="simulation",
        purpose=(
            "Compose one canonical saved-build DD action-damage provider for Combat "
            "Simulation from existing static build, skill, weapon-attack, periodic, "
            "mitigation, and execute services."
        ),
        implementation_path=(
            "services.combat_simulation_saved_build_dd_provider_service"
        ),
        inputs=(
            "PlayerBuild",
            "RotationPlan",
            "TargetResistance",
            "OptionalTargetCombatStateResolver",
            "OptionalTargetSnapshotResolver",
        ),
        outputs=("CombatSimulationSavedBuildDDProviderResolution",),
        dependencies=("simulation.outgoing_damage_bridge",),
        responsibilities=("combat_simulation_saved_build_dd_provider_composition",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Composition only. It does not duplicate skill, LA, HA, Ultimate, "
            "periodic, crit, penetration, mitigation, or execute formulas."
        ),
    ),
    ServiceDescriptor(
        service_id="simulation.saved_build_dd",
        domain="simulation",
        purpose=(
            "Run the deterministic Combat Simulation for one saved DD build while "
            "feeding canonical per-action damage evidence into explicit enemy Health."
        ),
        implementation_path="services.combat_simulation_saved_build_dd_service",
        inputs=(
            "EffectiveBuildSnapshot",
            "RotationPlan",
            "CombatSimulationTargetState",
            "TargetIdentity",
            "TargetResistance",
        ),
        outputs=("CombatSimulationResult",),
        dependencies=(
            "simulation.saved_build_dd_provider",
            "simulation.sequential_dd_health_feedback",
            "simulation.outgoing_damage_bridge",
        ),
        responsibilities=("combat_simulation_saved_build_dd_execution",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Unknown or unsupported canonical damage evidence remains unresolved and "
            "is never coerced to zero."
        ),
    ),
)


__all__ = ["COMBAT_SIMULATION_SERVICE_DESCRIPTORS"]
