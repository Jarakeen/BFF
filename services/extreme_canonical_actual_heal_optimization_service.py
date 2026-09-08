from __future__ import annotations

from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


class ExtremeCanonicalActualHealOptimizationService(ExtremeActualHealOptimizationService):
    """Standing Actual Heal optimizer with canonical heal-event aggregation.

    ``ExtremeActualHealOptimizationService`` owns the mature whole-build search.
    This subtype changes only its default healing-event evaluator so standing
    optimization uses the same reviewed recipient/time identity semantics as the
    conditional Extreme path.

    Explicitly injected optimizers and healing-event evaluators remain
    authoritative. The subtype therefore stays compatible with focused tests and
    callers that intentionally provide their own evaluation boundary.
    """

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        healing_events=None,
        **kwargs,
    ) -> None:
        core_optimizer = optimizer or ExtremeCompleteOptimizationService()
        canonical_events = healing_events or ExtremeCanonicalHealingEventService(
            database_path=core_optimizer.database_path
        )
        super().__init__(
            optimizer=core_optimizer,
            healing_events=canonical_events,
            **kwargs,
        )
