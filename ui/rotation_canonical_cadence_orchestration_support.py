from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhoodObligation,
)
from services.rotation_support_cadence_progression_runner_service import (
    RotationSupportCadenceProgressionRun,
)
from services.rotation_sustain_service import RotationSustainProjection
from ui.rotation_canonical_candidate_render_support import (
    RotationCanonicalCandidateRenderEvidence,
    RotationCanonicalCandidateRenderSupport,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateResult,
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest
from ui.rotation_support_cadence_progression_render_support import (
    RotationSupportCadenceProgressionRenderEvidence,
    RotationSupportCadenceProgressionRenderSupport,
)
from ui.rotation_support_cadence_runtime_support import (
    build_rotation_support_cadence_progression_runner,
)


class _CadenceRunner(Protocol):
    def run(self, **kwargs: object) -> RotationSupportCadenceProgressionRun: ...


@dataclass(frozen=True)
class RotationCanonicalCadenceOrchestrationResult:
    """One canonical rotation run plus optional cadence progression evidence."""

    canonical_result: RotationDashboardCanonicalCandidateResult
    canonical_evidence: RotationCanonicalCandidateRenderEvidence | None
    cadence_run: RotationSupportCadenceProgressionRun | None = None
    cadence_evidence: RotationSupportCadenceProgressionRenderEvidence | None = None

    @property
    def cadence_applied(self) -> bool:
        return self.cadence_run is not None

    @property
    def final_plan(self) -> RotationPlan | None:
        if self.cadence_evidence is not None:
            return self.cadence_evidence.plan
        if self.canonical_evidence is not None:
            return self.canonical_evidence.plan
        return None

    @property
    def final_sustain(self) -> RotationSustainProjection | None:
        if self.cadence_evidence is not None:
            return self.cadence_evidence.sustain_projection
        if self.canonical_evidence is not None:
            return self.canonical_evidence.sustain_projection
        return None


class RotationCanonicalCadenceOrchestrationSupport:
    """Compose canonical generation with optional support-cadence progression.

    The caller must supply a ready canonical evidence bundle. This service never
    invents encounter demands, uptime requirements, restoration evidence, role facts,
    or cadence obligations. Canonical evaluation always runs first. Optional
    ``role_evidence`` is forwarded to the dashboard candidate bridge; when its
    ``content_type`` is blank, the persisted content type already carried by the
    selected encounter bundle fills that one fact. No healer reliability or assignment
    exception is inferred here. Cadence progression begins only from the selected final
    stabilized canonical plan and sustain projection, and only when explicit cadence
    obligations are supplied.
    """

    def __init__(
        self,
        *,
        canonical_candidates: RotationDashboardCanonicalCandidateSupport | None = None,
        canonical_render: RotationCanonicalCandidateRenderSupport | None = None,
        cadence_runner: _CadenceRunner | None = None,
        cadence_render: RotationSupportCadenceProgressionRenderSupport | None = None,
    ) -> None:
        self.canonical_candidates = canonical_candidates or RotationDashboardCanonicalCandidateSupport()
        self.canonical_render = canonical_render or RotationCanonicalCandidateRenderSupport()
        self.cadence_runner = cadence_runner or build_rotation_support_cadence_progression_runner()
        self.cadence_render = cadence_render or RotationSupportCadenceProgressionRenderSupport()

    def run(
        self,
        *,
        player_build: PlayerBuild,
        generation_request: RotationGenerationRequest,
        evidence_bundle: RotationCanonicalEvidenceBundle,
        role_evidence: RotationCanonicalRoleEvidence | None = None,
        cadence_obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...] = (),
        cadence_priorities: AbilityPriorityList | None = None,
        cadence_evaluation_context: RotationSupportCadenceEvaluationContext | None = None,
        cadence_max_iterations: int = 8,
        character_id: str | None = None,
    ) -> RotationCanonicalCadenceOrchestrationResult:
        self._require_ready_bundle(evidence_bundle)
        effective_role_evidence = self._role_evidence_for_bundle(
            role_evidence,
            evidence_bundle,
        )

        canonical_result = self.canonical_candidates.run_effects(
            player_build=player_build,
            generation_request=generation_request,
            evaluator_resolver=evidence_bundle.evaluator_resolver,
            scorecard_resolver=evidence_bundle.scorecard_resolver,
            resource=evidence_bundle.resource,
            maximum_amount=evidence_bundle.maximum_amount,
            trigger_fraction=evidence_bundle.trigger_fraction,
            restoration_resolver=evidence_bundle.restoration_resolver,
            role_evidence=effective_role_evidence,
            demands=evidence_bundle.demands,
            options=evidence_bundle.options,
            wait_decision_factory=evidence_bundle.wait_decision_factory,
            requirements=evidence_bundle.requirements,
            passives=evidence_bundle.passives,
            reserve_assessment_resolver=evidence_bundle.reserve_assessment_resolver,
            max_iterations=evidence_bundle.max_iterations,
            baseline_id=evidence_bundle.baseline_id,
            character_id=character_id,
            coverage_report=evidence_bundle.coverage_report,
        )
        canonical_evidence = self.canonical_render.build(canonical_result.candidate_result)

        if canonical_evidence is None or not cadence_obligations:
            return RotationCanonicalCadenceOrchestrationResult(
                canonical_result=canonical_result,
                canonical_evidence=canonical_evidence,
            )

        cadence_run = self.cadence_runner.run(
            build=player_build,
            seed_plan=canonical_evidence.plan,
            seed_sustain=canonical_evidence.sustain_projection,
            obligations=tuple(cadence_obligations),
            max_iterations=int(cadence_max_iterations),
            priorities=cadence_priorities,
            evaluation_context=cadence_evaluation_context,
            effect_uptime_requirements=tuple(evidence_bundle.requirements),
            passives=tuple(evidence_bundle.passives),
            character_id=character_id,
        )
        cadence_evidence = self.cadence_render.build(cadence_run)
        return RotationCanonicalCadenceOrchestrationResult(
            canonical_result=canonical_result,
            canonical_evidence=canonical_evidence,
            cadence_run=cadence_run,
            cadence_evidence=cadence_evidence,
        )

    @staticmethod
    def _role_evidence_for_bundle(
        role_evidence: RotationCanonicalRoleEvidence | None,
        bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence | None:
        if role_evidence is None:
            return None
        if not isinstance(role_evidence, RotationCanonicalRoleEvidence):
            return role_evidence
        return role_evidence.with_content_type_if_missing(
            getattr(bundle, "content_type", "")
        )

    @staticmethod
    def _require_ready_bundle(bundle: RotationCanonicalEvidenceBundle) -> None:
        if bundle.ready:
            return
        details = [
            str(item).strip()
            for item in bundle.unresolved
            if str(item).strip()
        ]
        for gap in bundle.blocking_knowledge_gaps:
            summary = str(gap.summary or "").strip()
            needed = str(gap.needed_evidence or "").strip()
            if summary and needed:
                details.append(f"{summary} Bring back: {needed}")
            elif summary:
                details.append(summary)
        detail = "; ".join(details) or "unspecified unresolved evidence"
        raise ValueError(
            "canonical cadence orchestration requires a ready evidence bundle: " + detail
        )


__all__ = [
    "RotationCanonicalCadenceOrchestrationResult",
    "RotationCanonicalCadenceOrchestrationSupport",
]
