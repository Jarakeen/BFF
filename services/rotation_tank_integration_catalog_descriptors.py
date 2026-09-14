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
)


__all__ = ["ROTATION_TANK_INTEGRATION_SERVICE_DESCRIPTORS"]
