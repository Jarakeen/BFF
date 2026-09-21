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
        service_id="simulation.health_ordering",
        domain="simulation",
        purpose=(
            "Detect same-instant per-recipient Health consequences whose ordering "
            "is not proven by timestamp, priority, or sequence."
        ),
        implementation_path="services.combat_simulation_health_ordering_service",
        inputs=("CombatSimulationEventStream",),
        outputs=("CombatSimulationHealthOrderingCollision",),
        responsibilities=("combat_simulation_health_ordering_guard",),
        roles=("DD", "DPS", "Healer", "Tank"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "No alphabetical or source-name tie break is treated as ESO truth. "
            "Ambiguous same-instant Health state fails closed per recipient."
        ),
    ),
    ServiceDescriptor(
        service_id="simulation.deterministic_replay",
        domain="simulation",
        purpose=(
            "Run an identical deterministic Combat Simulation twice and compare "
            "the canonical deterministic signatures field by field."
        ),
        implementation_path=(
            "services.combat_simulation_deterministic_replay_service"
        ),
        inputs=("CombatSimulationRunner",),
        outputs=("CombatSimulationReplayVerification",),
        responsibilities=("combat_simulation_deterministic_replay_verification",),
        roles=("DD", "DPS", "Healer", "Tank"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "Verification reports exactly which canonical signature fields drift "
            "instead of reducing replay failure to a boolean."
        ),
    ),
    ServiceDescriptor(
        service_id="simulation.plan_attacker_state",
        domain="simulation",
        purpose=(
            "Project exact attacker CombatState from final-plan-owned evidence: "
            "active bar, explicitly scheduled potion actions, and reviewed persistent toggles."
        ),
        implementation_path="services.combat_simulation_plan_attacker_state_service",
        inputs=(
            "PlayerBuild",
            "CharacterProgression",
            "RotationPlan",
            "RuntimePoint",
        ),
        outputs=("RotationPlanRuntimeCombatStateResult",),
        responsibilities=("combat_simulation_plan_owned_attacker_state",),
        roles=("DD", "DPS", "Healer", "Tank"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Does not invent external proc, group-buff, encounter, or log-history "
            "state. Potion and persistent-toggle semantics remain owned by their "
            "existing Rotation services."
        ),
    ),
    ServiceDescriptor(
        service_id="simulation.damage_summary",
        domain="simulation",
        purpose=(
            "Summarize one completed Combat Simulation damage stream into target "
            "Health, kill time, source totals, and completeness-aware modeled DPS."
        ),
        implementation_path="services.combat_simulation_damage_summary_service",
        inputs=("CombatSimulationResult", "TargetIdentity"),
        outputs=("CombatSimulationDamageSummary",),
        responsibilities=("combat_simulation_damage_summary",),
        roles=("DD", "DPS", "Healer", "Tank"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Modeled DPS is withheld when unresolved damage evidence remains; the "
            "summary never relabels incomplete modeled damage as a complete parse."
        ),
    ),
    ServiceDescriptor(
        service_id="simulation.fight_termination",
        domain="simulation",
        purpose=(
            "Project the actually executed RotationPlan horizon when the simulated "
            "damage target dies before the planned rotation ends."
        ),
        implementation_path="services.combat_simulation_fight_termination_service",
        inputs=("RotationPlan", "TerminationTime", "TerminationSequence"),
        outputs=("RotationPlan",),
        responsibilities=("combat_simulation_fight_termination_projection",),
        roles=("DD", "DPS", "Healer", "Tank"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "The original plan remains immutable planning truth. The execution "
            "projection prevents downstream resource/healing/effect services from "
            "continuing beyond an already-proven terminal target death."
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
            "simulation.plan_attacker_state",
            "simulation.sequential_dd_health_feedback",
            "simulation.fight_termination",
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
