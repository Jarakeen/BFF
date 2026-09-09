from __future__ import annotations

from services.rotation_local_cadence_duration_refinement_service import (
    RotationLocalCadenceDurationRefinementService,
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
from ui.rotation_support_cadence_runtime_support import (
    build_rotation_support_cadence_progression_runner,
)


def test_runtime_factory_composes_local_cadence_progression_stack() -> None:
    runner = build_rotation_support_cadence_progression_runner()

    assert isinstance(runner, RotationSupportCadenceProgressionRunnerService)
    progression = runner.progression_service
    assert isinstance(progression, RotationSupportCadenceProgressionService)
    assert isinstance(progression.neighborhood_service, RotationSupportCadenceNeighborhoodService)
    assert isinstance(progression.evaluation_service, RotationSupportCadenceEvaluationService)
    assert isinstance(progression.recommendation_service, RotationSupportCadenceRecommendationService)
    assert isinstance(progression.effect_evidence_service, RotationSupportCadenceEffectEvidenceService)

    materializer = progression.neighborhood_service.materializer
    assert isinstance(materializer.duration_refiner, RotationLocalCadenceDurationRefinementService)
