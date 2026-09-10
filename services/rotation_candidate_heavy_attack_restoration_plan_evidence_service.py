from __future__ import annotations

from typing import Callable

from minmax.character_build.character_build import CharacterBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRestorationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
    RotationHeavyAttackRestorationEvidenceService,
)


RotationCandidateHeavyAttackCompletionEvidenceResolver = Callable[
    [GeneratedRotationCandidate],
    tuple[RotationHeavyAttackCompletionEvidence, ...],
]


class RotationCandidateHeavyAttackRestorationPlanEvidenceService:
    """Expose candidate-specific HA restoration to the canonical sustain composer.

    Canonical build/weapon identity and heavy-attack restoration math remain owned by
    the existing heavy-attack services. This adapter only evaluates the exact final
    candidate plan and translates that projection into the generic restoration
    evidence contract consumed by candidate sustain.

    A fixed completion-evidence tuple remains supported for one-plan callers. Candidate
    families whose heavy-attack schedules differ must provide a resolver so each exact
    candidate receives only evidence that belongs to its own scheduled heavies. The
    adapter never filters unrelated evidence silently because the lower-level
    restoration service deliberately treats such evidence as a structural mismatch.
    """

    def __init__(
        self,
        *,
        build: CharacterBuild,
        initial_bar: str,
        completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...] = (),
        completion_evidence_resolver: (
            RotationCandidateHeavyAttackCompletionEvidenceResolver | None
        ) = None,
        restoration_service: RotationHeavyAttackRestorationEvidenceService | None = None,
    ) -> None:
        self.build = build
        self.initial_bar = str(initial_bar or "").strip().casefold()
        if self.initial_bar not in {"front", "back"}:
            raise ValueError("rotation heavy-restoration initial_bar must be front or back")
        self.completion_evidence = tuple(completion_evidence)
        self.completion_evidence_resolver = completion_evidence_resolver
        if self.completion_evidence and self.completion_evidence_resolver is not None:
            raise ValueError(
                "rotation heavy-restoration completion evidence must use either a fixed tuple or a candidate resolver, not both"
            )
        self.restoration_service = (
            restoration_service or RotationHeavyAttackRestorationEvidenceService()
        )

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRestorationEvidence:
        projection = self.restoration_service.project(
            build=self.build,
            plan=candidate.plan,
            initial_bar=self.initial_bar,
            completion_evidence=self._completion_evidence_for(candidate),
        )
        violation_reasons = tuple(
            violation.reason for violation in projection.weapon_projection.violations
        )
        unresolved = self._dedupe(
            tuple(projection.unresolved) + violation_reasons
        )
        return RotationCandidateRestorationEvidence(
            candidate_id=candidate.candidate_id,
            restoration_events=tuple(projection.restoration_events),
            unresolved=unresolved,
        )

    def _completion_evidence_for(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> tuple[RotationHeavyAttackCompletionEvidence, ...]:
        if self.completion_evidence_resolver is None:
            return self.completion_evidence
        return tuple(self.completion_evidence_resolver(candidate))

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = [
    "RotationCandidateHeavyAttackCompletionEvidenceResolver",
    "RotationCandidateHeavyAttackRestorationPlanEvidenceService",
]
