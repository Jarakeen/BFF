from __future__ import annotations

from pathlib import Path

from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationCandidatePeriodicDamageTimingEvidenceService,
)
from services.rotation_dd_reviewed_skill_component_repository import (
    RotationDDReviewedSkillComponentRepository,
)


class RotationDDPeriodicDamageTimingEvidenceService(
    RotationCandidatePeriodicDamageTimingEvidenceService
):
    """DD timing evidence using the same reviewed component identity as DD damage.

    The generic timing service intentionally owns cadence/duration extraction only.
    DD damage classification can be stricter than the shared component repository,
    so the DD runtime path must inject the reviewed DD overlay or the evaluator and
    timing projector can disagree about whether one coefficient is periodic.
    """

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        super().__init__(
            path,
            component_repository=RotationDDReviewedSkillComponentRepository(path),
        )


__all__ = ["RotationDDPeriodicDamageTimingEvidenceService"]
