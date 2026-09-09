from __future__ import annotations

from minmax.rotation_effective_duration import RotationEffectiveDurationOverride

from services.rotation_local_cadence_duration_refinement_service import (
    RotationLocalCadenceDurationRefinementService,
)
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadenceCandidateService,
)
from services.rotation_support_cadence_effect_evidence_service import (
    RotationSupportCadenceEffectEvidenceService,
)
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationService,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhoodService,
)
from services.rotation_support_cadence_progression_runner_service import (
    RotationSupportCadenceProgressionRunnerService,
)
from services.rotation_support_cadence_progression_service import (
    RotationSupportCadenceProgressionService,
)
from services.rotation_support_cadence_recommendation_service import (
    RotationSupportCadenceRecommendationService,
)


def build_rotation_support_cadence_progression_runner(
    *,
    effective_duration_overrides: tuple[RotationEffectiveDurationOverride, ...] = (),
) -> RotationSupportCadenceProgressionRunnerService:
    """Compose the production support-cadence local-search stack.

    Mechanics remain owned by the existing services. This function only wires the
    tested production implementations together so UI/controller code does not grow a
    parallel service graph or accidentally fall back to the global duration refiner.
    Supply already-resolved duration evidence for the selected build, and construct
    a new runner when that build/evidence changes. No gear applicability is inferred.
    """

    materializer = RotationSupportCadenceCandidateService(
        RotationLocalCadenceDurationRefinementService(
            effective_duration_overrides=effective_duration_overrides,
        )
    )
    neighborhood = RotationSupportCadenceNeighborhoodService(materializer)
    evaluation = RotationSupportCadenceEvaluationService()
    recommendation = RotationSupportCadenceRecommendationService()
    effect_evidence = RotationSupportCadenceEffectEvidenceService()
    progression = RotationSupportCadenceProgressionService(
        neighborhood_service=neighborhood,
        evaluation_service=evaluation,
        recommendation_service=recommendation,
        effect_evidence_service=effect_evidence,
    )
    return RotationSupportCadenceProgressionRunnerService(progression)


__all__ = ["build_rotation_support_cadence_progression_runner"]
