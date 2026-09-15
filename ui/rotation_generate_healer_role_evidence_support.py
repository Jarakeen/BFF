from __future__ import annotations

"""Compose canonical healer role evidence at Generate time."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from engine.config import get_data_dir
from minmax.rotation_demand_window import RotationDemandKind
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_healer_canonical_role_output_factory_service import (
    RotationHealerCanonicalRoleOutputFactoryService,
)
from services.rotation_healer_channel_runtime_evidence_service import (
    RotationHealerReviewedChannelObservation,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelRuntimeEvidence,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerExternalConditionalDemandAssumption,
)
from services.rotation_healer_demand_criteria_service import (
    RotationCandidateHealerCriteriaHardObligationService,
    RotationHealerDemandCriterion,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
)
from services.rotation_recovery_healer_role_output_service import (
    RotationRecoveryHealerRoleOutputService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyStabilizedCandidateSnapshot,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle


PlanEvidenceFactory = Callable[..., object]


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


class _RotationGenerateRuntimeHealerPlanEvidenceProvider:
    """Re-evaluate healer-only final evidence from one stabilized runtime snapshot."""

    def __init__(
        self,
        *,
        static_provider: RotationCandidateCanonicalPlanEvidenceService,
        snapshot: RecoveryHeavyStabilizedCandidateSnapshot,
        recovery_role_output: RotationRecoveryHealerRoleOutputService,
        hard_obligation_provider: RotationCandidateHealerCriteriaHardObligationService | None,
    ) -> None:
        self.static_provider = static_provider
        self.snapshot = snapshot
        self.recovery_role_output = recovery_role_output
        self.hard_obligation_provider = hard_obligation_provider

    def evaluate_plan(self, candidate: GeneratedRotationCandidate):
        if candidate.candidate_id.casefold() != self.snapshot.candidate_id.casefold():
            raise ValueError(
                "stabilized healer plan-evidence candidate mismatch: "
                f"expected {self.snapshot.candidate_id!r}, got {candidate.candidate_id!r}"
            )
        if candidate.plan != self.snapshot.plan:
            raise ValueError(
                "stabilized healer plan-evidence provider requires the exact final plan"
            )

        evidence = self.static_provider.evaluate_plan(candidate)
        role_output = self.recovery_role_output.evaluate_snapshot(self.snapshot)
        if role_output.candidate_id.casefold() != candidate.candidate_id.casefold():
            raise ValueError(
                "stabilized healer role-output candidate mismatch: "
                f"expected {candidate.candidate_id!r}, got {role_output.candidate_id!r}"
            )

        updates = {
            "role_output_value": role_output.resolved_value,
            "role_output_unresolved": tuple(role_output.unresolved),
        }
        if self.hard_obligation_provider is not None:
            runtime_resolver = (
                self.recovery_role_output.runtime_build_context_resolver_for_snapshot(
                    self.snapshot
                )
            )
            hard_obligation = self.hard_obligation_provider.evaluate_plan(
                candidate,
                runtime_build_context_resolver=runtime_resolver,
            )
            if hard_obligation.candidate_id.casefold() != candidate.candidate_id.casefold():
                raise ValueError(
                    "stabilized healer hard-obligation candidate mismatch: "
                    f"expected {candidate.candidate_id!r}, got {hard_obligation.candidate_id!r}"
                )
            updates.update(
                role_hard_obligation_satisfied=hard_obligation.satisfied,
                role_hard_obligation_reasons=tuple(hard_obligation.reasons),
            )
        return replace(evidence, **updates)


class _RotationGenerateHealerPlanEvidenceProvider:
    """Bind canonical healer output to the final recovery-stabilized snapshot."""

    def __init__(
        self,
        *,
        static_provider: RotationCandidateCanonicalPlanEvidenceService,
        recovery_role_output: RotationRecoveryHealerRoleOutputService,
        hard_obligation_provider: RotationCandidateHealerCriteriaHardObligationService | None,
    ) -> None:
        self.static_provider = static_provider
        self.recovery_role_output = recovery_role_output
        self.hard_obligation_provider = hard_obligation_provider

    def evaluate_plan(self, candidate: GeneratedRotationCandidate):
        return self.static_provider.evaluate_plan(candidate)

    def for_stabilized_snapshot(
        self,
        snapshot: RecoveryHeavyStabilizedCandidateSnapshot,
    ):
        if snapshot.runtime_combat_state_resolver is None:
            return self.static_provider
        return _RotationGenerateRuntimeHealerPlanEvidenceProvider(
            static_provider=self.static_provider,
            snapshot=snapshot,
            recovery_role_output=self.recovery_role_output,
            hard_obligation_provider=self.hard_obligation_provider,
        )


class RotationGenerateHealerRoleEvidenceSupport:
    """Join a selected healer build to explicit canonical healing demands.

    Encounter thresholds and windows remain owned by the evidence bundle. Reviewed
    runtime observations and external-conditional assumptions remain explicit caller
    inputs. This composer does not infer group-healing reliability, assignments,
    target counts, phase names, or encounter policy from display text. Explicit
    reviewed healer criteria reuse the same window output as a separate hard gate;
    caller assumptions never become authoritative through this bridge.

    Production canonical plan evidence is runtime-bindable: after recovery stabilization,
    healer output and verified healer criteria are recomputed from the exact final-plan
    runtime build context. Sustain, duration, and unrelated evidence remain owned by the
    ordinary canonical plan-evidence service. Injected/custom plan-evidence factories
    keep their supplied shape unchanged.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        role_output_factory: RotationHealerCanonicalRoleOutputFactoryService | None = None,
        plan_evidence_factory: PlanEvidenceFactory | None = None,
        runtime_build_context_service: RotationPlanRuntimeBuildContextService | None = None,
        reviewed_runtime_observations: tuple[
            RotationHealerReviewedRuntimeObservation, ...
        ] = (),
        delayed_runtime_evidence: tuple[
            RotationHealerDelayedRuntimeEvidence, ...
        ] = (),
        channel_runtime_evidence: tuple[
            RotationHealerChannelRuntimeEvidence, ...
        ] = (),
        reviewed_channel_observations: tuple[
            RotationHealerReviewedChannelObservation, ...
        ] = (),
        external_conditional_assumptions: tuple[
            RotationHealerExternalConditionalDemandAssumption, ...
        ] = (),
        criteria: tuple[RotationHealerDemandCriterion, ...] = (),
        reliable_group_healing: bool | None = None,
        exception_contexts: tuple[str, ...] = (),
        role_output_label: str = "healing demand coverage",
        assigned_support_label: str = "assigned support coverage",
    ) -> None:
        database = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.role_output_factory = (
            role_output_factory
            or RotationHealerCanonicalRoleOutputFactoryService(
                database_path=database,
            )
        )
        self.plan_evidence_factory = (
            plan_evidence_factory or RotationCandidateCanonicalPlanEvidenceService
        )
        self.runtime_build_context_service = runtime_build_context_service
        if (
            self.runtime_build_context_service is None
            and isinstance(
                self.role_output_factory,
                RotationHealerCanonicalRoleOutputFactoryService,
            )
        ):
            self.runtime_build_context_service = RotationPlanRuntimeBuildContextService(
                static_context_service=self.role_output_factory.static_context_service,
            )
        self.reviewed_runtime_observations = tuple(reviewed_runtime_observations)
        self.delayed_runtime_evidence = tuple(delayed_runtime_evidence)
        self.channel_runtime_evidence = tuple(channel_runtime_evidence)
        self.reviewed_channel_observations = tuple(reviewed_channel_observations)
        self.external_conditional_assumptions = tuple(
            external_conditional_assumptions
        )
        self.criteria = tuple(criteria)
        self.reliable_group_healing = reliable_group_healing
        self.exception_contexts = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in exception_contexts
                if str(item).strip()
            )
        )
        self.role_output_label = self._required_label(
            role_output_label,
            "role_output_label",
        )
        self.assigned_support_label = self._required_label(
            assigned_support_label,
            "assigned_support_label",
        )

    def compose(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence:
        role_key = _canonical_role(getattr(player_build, "Role", ""))
        if role_key not in {"heal", "healer"}:
            raise ValueError(
                "automatic healer role evidence requires an explicit healer saved-build role"
            )

        healing_demands = tuple(
            demand
            for demand in evidence_bundle.demands
            if demand.kind is RotationDemandKind.HEALING
        )
        if not healing_demands:
            raise ValueError(
                "automatic healer role evidence requires at least one canonical healing demand"
            )

        role_output = self.role_output_factory.build(
            build=player_build,
            demands=healing_demands,
            reviewed_runtime_observations=self.reviewed_runtime_observations,
            delayed_runtime_evidence=self.delayed_runtime_evidence,
            channel_runtime_evidence=self.channel_runtime_evidence,
            reviewed_channel_observations=self.reviewed_channel_observations,
            external_conditional_assumptions=self.external_conditional_assumptions,
        )
        if role_output.role_output_provider is None:
            detail = "; ".join(role_output.unresolved) or "role-output provider unavailable"
            raise ValueError("canonical healer role output is unavailable: " + detail)

        hard_obligation_provider = None
        plan_kwargs = {
            "build": player_build,
            "resource": evidence_bundle.resource,
            "role_output_evidence_provider": role_output,
        }
        if self.criteria:
            hard_obligation_provider = RotationCandidateHealerCriteriaHardObligationService(
                multi_demand_output_service=role_output,
                criteria=self.criteria,
            )
            plan_kwargs["role_hard_obligation_evidence_provider"] = (
                hard_obligation_provider
            )
        plan_evidence = self.plan_evidence_factory(**plan_kwargs)
        if (
            isinstance(plan_evidence, RotationCandidateCanonicalPlanEvidenceService)
            and self.runtime_build_context_service is not None
        ):
            plan_evidence = _RotationGenerateHealerPlanEvidenceProvider(
                static_provider=plan_evidence,
                recovery_role_output=RotationRecoveryHealerRoleOutputService(
                    build=player_build,
                    role_output_service=role_output,
                    runtime_build_context_service=self.runtime_build_context_service,
                ),
                hard_obligation_provider=hard_obligation_provider,
            )
        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=plan_evidence,
            role_output_label=self.role_output_label,
            assigned_support_label=self.assigned_support_label,
            content_type=str(evidence_bundle.content_type or "").strip(),
            reliable_group_healing=self.reliable_group_healing,
            exception_contexts=self.exception_contexts,
            role_key=role_key,
        )

    @staticmethod
    def _required_label(value: object, field_name: str) -> str:
        label = str(value or "").strip()
        if not label:
            raise ValueError(f"{field_name} must be non-empty")
        return label


__all__ = ["RotationGenerateHealerRoleEvidenceSupport"]
