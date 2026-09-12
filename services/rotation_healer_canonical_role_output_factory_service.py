from __future__ import annotations

"""Compose saved-build healer mechanics into reusable whole-plan role evidence."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandWindow
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerDemandWindowOutput,
    RotationCandidateHealerMultiDemandOutput,
    RotationCandidateHealerMultiDemandRoleOutputService,
)
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
    RotationCandidateHealerDemandEvidenceProvider,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelRuntimeEvidence,
)
from services.rotation_healer_channel_runtime_evidence_service import (
    RotationHealerReviewedChannelObservation,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerExternalConditionalDemandAssumption,
)
from services.rotation_healer_output_context_relevance_service import (
    RotationHealerOutputContextRelevance,
    RotationHealerOutputContextRelevanceService,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextResolution,
    RotationStaticBuildContextService,
)


HealerDemandEvidenceFactory = Callable[..., RotationCandidateHealerDemandEvidenceProvider]


@dataclass(frozen=True)
class RotationHealerCanonicalRoleOutputFactoryResult:
    """Reusable healer output provider plus its exact static-context boundary."""

    static_context: RotationStaticBuildContextResolution
    context_relevance: RotationHealerOutputContextRelevance
    demand_evidence_provider: RotationCandidateHealerDemandEvidenceProvider | None
    role_output_provider: RotationCandidateHealerMultiDemandRoleOutputService | None
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.role_output_provider is not None and not self.unresolved

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRoleOutputEvidence:
        """Expose fail-closed aggregate output to canonical plan evidence."""

        output = self.evaluate_windows(candidate)
        return RotationCandidateRoleOutputEvidence(
            candidate_id=output.candidate_id,
            value=output.weakest_window_value,
            unresolved=output.unresolved,
        )

    def evaluate_windows(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateHealerMultiDemandOutput:
        provider = self.role_output_provider
        if provider is None:
            detail = "; ".join(self.unresolved) or "healer role-output provider unavailable"
            raise ValueError("canonical healer role output is unavailable: " + detail)

        output = provider.evaluate_windows(candidate)
        if not self.unresolved:
            return output
        blockers = tuple(
            f"static healer-output context: {message}"
            for message in self.unresolved
        )
        blocked_windows = tuple(
            RotationCandidateHealerDemandWindowOutput(
                evidence=replace(
                    window.evidence,
                    unresolved=tuple(
                        dict.fromkeys(tuple(window.unresolved) + blockers)
                    ),
                ),
                modeled_healing_per_demand_second=None,
            )
            for window in output.windows
        )
        return RotationCandidateHealerMultiDemandOutput(
            candidate_id=output.candidate_id,
            windows=blocked_windows,
            unresolved=tuple(
                dict.fromkeys(tuple(output.unresolved) + blockers)
            ),
        )


class RotationHealerCanonicalRoleOutputFactoryService:
    """Build canonical multi-demand healer output without encounter-specific policy.

    The caller owns the exact healing demand windows and any reviewed runtime evidence
    or explicit conditional assumptions. This service resolves the selected saved
    build through the shared static context pipeline, classifies context diagnostics,
    and composes the existing canonical healer demand and multi-window output services.

    Xalvakka thresholds, target counts, raid DPS, difficulty, phase names, and Minor
    Lifesteal attacker counts are deliberately absent. Those remain encounter or
    caller policy. Relevant static-context gaps are retained as output blockers;
    diagnostics already proven irrelevant to modeled healing remain inspectable as
    ambient evidence.
    """

    def __init__(
        self,
        *,
        database_path: str | Path,
        static_context_service: RotationStaticBuildContextService | None = None,
        context_relevance_service: RotationHealerOutputContextRelevanceService | None = None,
        demand_evidence_factory: HealerDemandEvidenceFactory | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.static_context_service = (
            static_context_service
            or RotationStaticBuildContextService(database_path=self.database_path)
        )
        self.context_relevance_service = (
            context_relevance_service or RotationHealerOutputContextRelevanceService()
        )
        self.demand_evidence_factory = (
            demand_evidence_factory
            or RotationCandidateHealerCanonicalDemandEvidenceProvider
        )

    def build(
        self,
        *,
        build: PlayerBuild,
        demands: tuple[RotationDemandWindow, ...],
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
    ) -> RotationHealerCanonicalRoleOutputFactoryResult:
        demand_tuple = tuple(demands)
        if not demand_tuple:
            raise ValueError("canonical healer role output requires at least one demand")
        if any(demand.kind is not RotationDemandKind.HEALING for demand in demand_tuple):
            raise ValueError("canonical healer role output accepts only healing demands")

        static_context = self.static_context_service.resolve(build)
        relevance = self.context_relevance_service.classify(static_context.unresolved)
        front = static_context.context_for("front")
        back = static_context.context_for("back")

        unresolved = list(relevance.relevant)
        if front is None:
            unresolved.append("front canonical static context is unavailable")
        if back is None:
            unresolved.append("back canonical static context is unavailable")
        unresolved_tuple = tuple(dict.fromkeys(unresolved))

        if front is None or back is None:
            return RotationHealerCanonicalRoleOutputFactoryResult(
                static_context=static_context,
                context_relevance=relevance,
                demand_evidence_provider=None,
                role_output_provider=None,
                unresolved=unresolved_tuple,
            )

        demand_provider = self.demand_evidence_factory(
            database_path=self.database_path,
            build=build,
            context=front,
            contexts_by_bar={"front": front, "back": back},
            reviewed_runtime_observations=tuple(reviewed_runtime_observations),
            delayed_runtime_evidence=tuple(delayed_runtime_evidence),
            channel_runtime_evidence=tuple(channel_runtime_evidence),
            reviewed_channel_observations=tuple(reviewed_channel_observations),
            external_conditional_assumptions=tuple(
                external_conditional_assumptions
            ),
        )
        role_output = RotationCandidateHealerMultiDemandRoleOutputService(
            demands=demand_tuple,
            demand_evidence_provider=demand_provider,
        )
        return RotationHealerCanonicalRoleOutputFactoryResult(
            static_context=static_context,
            context_relevance=relevance,
            demand_evidence_provider=demand_provider,
            role_output_provider=role_output,
            unresolved=unresolved_tuple,
        )


__all__ = [
    "RotationHealerCanonicalRoleOutputFactoryResult",
    "RotationHealerCanonicalRoleOutputFactoryService",
]
