from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_ability_priority import AbilityPriorityList
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhoodObligation,
)
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
)


@dataclass(frozen=True)
class RotationGenerateCanonicalContext:
    """Explicit encounter-aware inputs used by the dashboard Generate action.

    Presence of this object opts Generate Rotation into canonical encounter-aware
    orchestration. Absence preserves the legacy/plain generation path. The context
    contains policy/runtime inputs only; it does not infer them from role, class,
    encounter display names, or UI labels.
    """

    evidence_inputs: RotationSelectedEncounterEvidenceInputs
    cadence_obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...] = ()
    cadence_priorities: AbilityPriorityList | None = None
    cadence_evaluation_context: RotationSupportCadenceEvaluationContext | None = None
    cadence_max_iterations: int = 8
    character_id: str | None = None

    def __post_init__(self) -> None:
        iterations = int(self.cadence_max_iterations)
        if iterations <= 0:
            raise ValueError("cadence_max_iterations must be positive")
        object.__setattr__(self, "cadence_max_iterations", iterations)
        object.__setattr__(self, "cadence_obligations", tuple(self.cadence_obligations))


__all__ = ["RotationGenerateCanonicalContext"]
