from __future__ import annotations

from copy import copy

from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryRuntimeOutputConditionContextResolverFactory,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport


class _ConditionalOutputPipelineDelegate:
    """Inject one explicit output-condition factory into an existing pipeline call."""

    def __init__(self, pipeline, resolver_factory) -> None:
        self.pipeline = pipeline
        self.resolver_factory = resolver_factory

    def run_effects(self, **kwargs):
        kwargs["runtime_output_condition_context_resolver_factory"] = self.resolver_factory
        return self.pipeline.run_effects(**kwargs)


class RotationCanonicalCandidateConditionalOutputSupport(RotationCanonicalCandidateSupport):
    """Application adapter for exact-event conditional output evidence.

    The canonical candidate bridge intentionally remains ignorant of condition names
    and geometry. When an authoritative per-plan resolver factory is supplied, this
    adapter binds it only at the pipeline boundary that already owns stabilized runtime
    resolver factories. A shallow per-run copy avoids mutating the shared support
    instance or leaking one caller's resolver into another candidate evaluation.
    """

    def run_effects(
        self,
        *,
        runtime_output_condition_context_resolver_factory: (
            RecoveryRuntimeOutputConditionContextResolverFactory | None
        ) = None,
        **kwargs,
    ):
        if runtime_output_condition_context_resolver_factory is None:
            return super().run_effects(**kwargs)

        bound = copy(self)
        bound.pipeline = _ConditionalOutputPipelineDelegate(
            self.pipeline,
            runtime_output_condition_context_resolver_factory,
        )
        return RotationCanonicalCandidateSupport.run_effects(bound, **kwargs)


__all__ = ["RotationCanonicalCandidateConditionalOutputSupport"]
