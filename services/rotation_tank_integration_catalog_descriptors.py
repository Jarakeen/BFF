from __future__ import annotations

"""Catalog metadata for Tank Rotation Builder integration/orchestration services."""

from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


ROTATION_TANK_INTEGRATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.tank.provider_scope",
        domain="rotation",
        purpose=(
            "Recompute canonical Phase 10/11 provider ownership for the exact selected Tank, "
            "selected-team saved builds, and selected encounter, then require an explicit "
            "rotation-policy disposition for every owned assignment."
        ),
        implementation_path="services.rotation_tank_provider_scope_service",
        inputs=(
            "PlayerBuild",
            "SelectedTeamSavedBuilds",
            "EncounterId",
            "RotationAssignmentPolicyBundle",
        ),
        outputs=("RotationTankProviderScopeResolution",),
        dependencies=(
            "rotation.assignment_policy.registry",
        ),
        responsibilities=(
            "rotation_tank_selected_team_provider_scope_resolution",
            "rotation_tank_assignment_policy_readiness",
        ),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Provider ownership remains owned by the existing Phase 10/11 capability, roster, "
            "candidate, and assignment pipeline. Missing executable policy stays unresolved; "
            "the service never derives strategy from role names or roster labels."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.family_projection",
        domain="rotation",
        purpose=(
            "Compose explicitly supplied discrete-taunt, continuous-taunt-maintenance, and "
            "defensive-response strategies into one candidate-family projector used before "
            "recovery replay and final Tank obligation evaluation."
        ),
        implementation_path="services.rotation_tank_family_projector_service",
        inputs=(
            "RotationTankTauntActionClaim",
            "RotationTankTauntMaintenanceRefreshPolicy",
            "RotationTankDefensiveActionClaim",
            "RotationActionSlotRequirement",
        ),
        outputs=("RotationCandidateFamilyProjector",),
        dependencies=(
            "rotation.tank.taunt_family_projection",
            "rotation.tank.taunt_maintenance_family_projection",
            "rotation.tank.defensive_family_projection",
        ),
        responsibilities=("rotation_tank_explicit_strategy_family_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Only explicit caller-owned strategy activates a projection lane. Obligation evidence "
            "alone never invents taunt timing, refresh lead, bar, target identity, or block/dodge timing."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_add_activity_context",
        domain="rotation",
        purpose=(
            "Project reviewed encounter add-activity boundaries onto already-bound Tank "
            "responsibilities as contextual Generate triggers without inventing wall-clock timing."
        ),
        implementation_path="services.rotation_tank_encounter_add_activity_trigger_service",
        inputs=(
            "RaidTankEncounterBoundResponsibility",
            "ReviewedEncounterAddActivity",
        ),
        outputs=("RotationTankEncounterAddActivityTrigger",),
        responsibilities=("rotation_tank_reviewed_add_activity_context",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "These rows indicate when reviewed add responsibility becomes relevant from observed "
            "actor activity. They do not create spawn timestamps, taunt timestamps, uptime floors, "
            "or hard rotation obligations."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_add_taunt_handling_context",
        domain="rotation",
        purpose=(
            "Project reviewed actor-specific add-taunt handling classifications onto exact bound "
            "Tank responsibilities for ranking/context consumers."
        ),
        implementation_path=(
            "services.rotation_tank_encounter_add_taunt_handling_context_service"
        ),
        inputs=(
            "RaidTankEncounterBoundResponsibility",
            "ReviewedAddTauntHandlingActor",
        ),
        outputs=("RotationTankAddTauntHandlingContext",),
        responsibilities=("rotation_tank_reviewed_add_taunt_handling_context",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Actor handling classes remain contextual evidence only. Single-report behavior is not "
            "promoted into hard maintenance obligations, exact timing, or canonical mechanic truth."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.tank.encounter_priority_context",
        domain="rotation",
        purpose=(
            "Order already-reviewed, already-bound Tank responsibilities into soft rotation-facing "
            "priority cues while preserving ownership, actor context, and trigger semantics."
        ),
        implementation_path="services.rotation_tank_encounter_priority_context_service",
        inputs=(
            "RaidTankEncounterBoundResponsibility",
            "RotationTankAddTauntHandlingContext",
        ),
        outputs=("RotationTankEncounterPriorityCue",),
        dependencies=("rotation.tank.encounter_add_taunt_handling_context",),
        responsibilities=("rotation_tank_encounter_priority_context",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
        notes=(
            "Priority cues are consumer-owned strategy context. They never become hard policy, "
            "cross-lane taunt permission, timing windows, or uptime floors by themselves."
        ),
    ),
    ServiceDescriptor(
        service_id="raid_plan.tank.triggered_responsibility_projection",
        domain="raid_plan",
        purpose=(
            "Project reviewed Tank add-activity and soft priority context into seat-owned "
            "runtime-triggered Raid Plan responsibilities without manufacturing Rotation timestamps."
        ),
        implementation_path="services.raid_plan_tank_triggered_responsibility_service",
        inputs=(
            "RaidPlanSeatId",
            "RotationTankEncounterAddActivityTrigger",
            "RotationTankEncounterPriorityCue",
        ),
        outputs=(
            "RaidPlanTankTriggeredResponsibilityProjection",
            "RaidPlanTriggeredResponsibility",
        ),
        dependencies=(
            "rotation.tank.encounter_add_activity_context",
            "rotation.tank.encounter_priority_context",
        ),
        responsibilities=("raid_plan_tank_runtime_triggered_responsibility_projection",),
        roles=("Tank",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Only reviewed add activity paired with unambiguous reviewed_add_activity priority "
            "context becomes plan intent. Responsibilities requiring additional encounter context "
            "remain unresolved, and no output from this service carries time_seconds or hard policy."
        ),
    ),
)


__all__ = ["ROTATION_TANK_INTEGRATION_SERVICE_DESCRIPTORS"]
