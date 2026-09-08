from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationPlan
from services.rotation_effect_uptime_service import RotationEffectUptimeAssessment
from services.rotation_sustain_service import RotationSustainProjection
from ui.rotation_canonical_candidate_support import (
    RotationCanonicalCandidateApplicationResult,
)
from ui.rotation_duration_evidence_support import (
    RotationDurationEvidence,
    RotationDurationEvidenceSupport,
)


@dataclass(frozen=True)
class RotationCanonicalCandidateRenderEvidence:
    """Final post-recovery evidence safe for dashboard rendering.

    Every field is tied to the selected stabilized candidate. Seed-generation
    evidence is intentionally excluded so the dashboard cannot mix a final plan
    with stale pre-recovery sustain, duration, or effect measurements.
    """

    candidate_id: str
    plan: RotationPlan
    sustain_projection: RotationSustainProjection
    duration_evidence: RotationDurationEvidence
    effect_uptime_assessments: tuple[RotationEffectUptimeAssessment, ...]


class RotationCanonicalCandidateRenderSupport:
    """Join final canonical selection to evidence that describes that exact plan.

    Sustain evidence comes directly from the selected stabilized snapshot's final
    recovery replay, which is already the authoritative Phase 4 rerun with every
    caller-verified restoration event applied. Ordinary duration-card evidence is
    rebuilt from the selected final plan. Build-aware effect assessments come from
    the final family evaluation, which reassesses effects only after stabilization.

    No candidate is renderable unless the canonical pipeline selected it.
    """

    def __init__(
        self,
        *,
        duration_evidence: RotationDurationEvidenceSupport | None = None,
    ) -> None:
        self.duration_evidence = duration_evidence or RotationDurationEvidenceSupport()

    def build(
        self,
        result: RotationCanonicalCandidateApplicationResult,
    ) -> RotationCanonicalCandidateRenderEvidence | None:
        pipeline = result.pipeline_result
        if pipeline is None or pipeline.selected_candidate is None:
            return None

        selected = pipeline.selected_candidate
        if not selected.selectable:
            raise ValueError(
                "canonical rotation render requested for a nonselectable candidate"
            )

        selected_id = str(selected.candidate_id or "").strip()
        if not selected_id:
            raise ValueError("selected canonical rotation candidate_id is empty")

        matches = tuple(
            snapshot
            for snapshot in pipeline.stabilized_candidates
            if str(snapshot.candidate_id).casefold() == selected_id.casefold()
        )
        if len(matches) != 1:
            raise ValueError(
                "selected canonical rotation candidate does not map to exactly one "
                "final stabilized snapshot"
            )
        snapshot = matches[0]

        evaluation = selected.evaluation
        evaluation_id = str(getattr(evaluation, "candidate_id", "") or "").strip()
        if evaluation_id.casefold() != selected_id.casefold():
            raise ValueError(
                "selected canonical rotation evaluation identity does not match "
                "the selected candidate"
            )

        assessments = tuple(
            getattr(evaluation, "effect_uptime_assessments", ()) or ()
        )
        return RotationCanonicalCandidateRenderEvidence(
            candidate_id=selected_id,
            plan=snapshot.plan,
            sustain_projection=snapshot.replay.final_projection,
            duration_evidence=self.duration_evidence.build(snapshot.plan),
            effect_uptime_assessments=assessments,
        )


__all__ = [
    "RotationCanonicalCandidateRenderEvidence",
    "RotationCanonicalCandidateRenderSupport",
]
