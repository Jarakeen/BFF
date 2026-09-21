from __future__ import annotations

"""DD-specific relevance adapter over canonical static build context resolution."""

from dataclasses import replace

from services.rotation_dd_output_context_relevance_service import (
    RotationDDOutputContextRelevanceService,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextResolution,
    RotationStaticBuildContextService,
)


class RotationDDRelevantStaticContextService:
    """Keep only unresolved static facts that can affect modeled DD damage.

    The underlying static-context service remains authoritative for build state. This
    adapter changes only the unresolved diagnostic surface for DD consumers so known
    ambient movement/healing/max-health diagnostics do not block damage evaluation.
    Unknown or offensive diagnostics remain unresolved and therefore fail closed.
    """

    def __init__(
        self,
        delegate: RotationStaticBuildContextService,
        *,
        relevance_service: RotationDDOutputContextRelevanceService | None = None,
    ) -> None:
        self.delegate = delegate
        self.relevance_service = relevance_service or RotationDDOutputContextRelevanceService()

    def resolve(self, player_build, **kwargs) -> RotationStaticBuildContextResolution:
        result = self.delegate.resolve(player_build, **kwargs)
        relevance = self.relevance_service.classify(result.unresolved)
        unresolved = tuple(relevance.relevant)
        if not result.progression.resolved:
            unresolved = tuple(
                dict.fromkeys((*result.progression.unresolved, *unresolved))
            )
        return replace(result, unresolved=unresolved)


__all__ = ["RotationDDRelevantStaticContextService"]
