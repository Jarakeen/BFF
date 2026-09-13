from __future__ import annotations

"""Compose stabilized runtime output conditions into DD Generate evidence.

This adapter deliberately owns composition only. The existing DD Generate support
continues to build canonical skill/weapon damage evaluators. This layer recognizes
that explicit runtime ``ConditionContext`` is another reason to rebind final-plan
evidence after stabilization and decorates the already-built periodic projection
service with the shared fail-closed conditional-output bridge.

No condition name is interpreted here and no skill-specific geometry, cadence, or
magnitude is inferred.
"""

from dataclasses import replace
from typing import Protocol

from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild
from services.rotation_candidate_periodic_damage_conditional_output_service import (
    RotationCandidatePeriodicDamageConditionalOutputService,
)
from services.rotation_runtime_output_eligibility_service import (
    RotationRuntimeOutputConditionContextResolver,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle


class _DDRoleEvidenceComposer(Protocol):
    def compose(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence: ...


def _bind_condition_aware_periodic_projection(
    plan_evidence_provider,
    condition_context_resolver: RotationRuntimeOutputConditionContextResolver | None,
):
    """Decorate the existing skill periodic projection without replacing DD math."""

    role_output = getattr(plan_evidence_provider, "role_output_evidence_provider", None)
    action_router = getattr(role_output, "action_damage_evidence_provider", None)
    providers = getattr(action_router, "_providers", None)
    if not isinstance(providers, dict):
        raise ValueError(
            "DD conditional output composition requires the canonical action damage router"
        )

    skill_provider = providers.get(RotationActionKind.SKILL)
    if skill_provider is None:
        raise ValueError(
            "DD conditional output composition requires the canonical skill damage provider"
        )

    projection = getattr(skill_provider, "periodic_runtime_projection_service", None)
    if projection is None:
        return plan_evidence_provider

    if isinstance(
        projection,
        RotationCandidatePeriodicDamageConditionalOutputService,
    ):
        # A caller may deliberately pre-compose the same bridge. Do not stack filters.
        projection.condition_context_resolver = condition_context_resolver
        return plan_evidence_provider

    skill_provider.periodic_runtime_projection_service = (
        RotationCandidatePeriodicDamageConditionalOutputService(
            projection,
            condition_context_resolver=condition_context_resolver,
        )
    )
    return plan_evidence_provider


class _RotationGenerateDDConditionAwareSnapshotPlanEvidenceProvider:
    """Rebind final DD evidence when condition context is the only runtime fact."""

    def __init__(self, base_snapshot_provider) -> None:
        static_provider = getattr(base_snapshot_provider, "static_provider", None)
        runtime_provider_factory = getattr(
            base_snapshot_provider,
            "runtime_provider_factory",
            None,
        )
        if static_provider is None or runtime_provider_factory is None:
            raise ValueError(
                "DD conditional output support requires snapshot-aware base plan evidence"
            )

        self.static_provider = _bind_condition_aware_periodic_projection(
            static_provider,
            None,
        )
        self.runtime_provider_factory = runtime_provider_factory

    @property
    def role_output_evidence_provider(self):
        return self.static_provider.role_output_evidence_provider

    def evaluate_plan(self, candidate):
        return self.static_provider.evaluate_plan(candidate)

    def for_stabilized_snapshot(self, snapshot):
        condition_context_resolver = getattr(
            snapshot,
            "runtime_output_condition_context_resolver",
            None,
        )
        if (
            getattr(snapshot, "runtime_combat_state_resolver", None) is None
            and getattr(snapshot, "runtime_target_combat_state_resolver", None) is None
            and getattr(snapshot, "runtime_target_resistance_resolver", None) is None
            and getattr(snapshot, "runtime_activation_anchor_resolver", None) is None
            and condition_context_resolver is None
        ):
            return self.static_provider

        runtime_provider = self.runtime_provider_factory(snapshot)
        return _bind_condition_aware_periodic_projection(
            runtime_provider,
            condition_context_resolver,
        )


class RotationGenerateDDConditionalOutputSupport:
    """Decorate canonical DD Generate role evidence with runtime output conditions."""

    def __init__(self, base_support: _DDRoleEvidenceComposer) -> None:
        self.base_support = base_support

    def compose(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence:
        evidence = self.base_support.compose(
            player_build=player_build,
            evidence_bundle=evidence_bundle,
        )
        return replace(
            evidence,
            plan_evidence_provider=(
                _RotationGenerateDDConditionAwareSnapshotPlanEvidenceProvider(
                    evidence.plan_evidence_provider
                )
            ),
        )


__all__ = ["RotationGenerateDDConditionalOutputSupport"]
