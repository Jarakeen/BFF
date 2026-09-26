from __future__ import annotations

"""Append one proven local runtime-state family to generated sustained-DPS search."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_runtime_effect_relevance_service import (
    ExtremeSustainedDPSRuntimeEffectRelevance,
)
from services.extreme_sustained_dps_runtime_effect_scaling_service import (
    ExtremeSustainedDPSRuntimeEffectScalingResult,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontier,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedRuntimeStateLeaf:
    pipeline_state: object
    runtime_state_choice: ExtremeSustainedDPSRuntimeStateChoice
    omitted_scope: tuple[str, ...]
    relevance: ExtremeSustainedDPSRuntimeEffectRelevance | None = None
    scaling: ExtremeSustainedDPSRuntimeEffectScalingResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_state_choice, ExtremeSustainedDPSRuntimeStateChoice):
            raise TypeError("generated runtime-state leaf requires a canonical runtime-state choice")
        if not isinstance(self.omitted_scope, tuple):
            raise TypeError("generated runtime-state leaf omitted_scope must be a tuple")
        if self.relevance is not None and not isinstance(
            self.relevance, ExtremeSustainedDPSRuntimeEffectRelevance
        ):
            raise TypeError("generated runtime-state leaf relevance must be canonical when supplied")
        if self.scaling is not None and not isinstance(
            self.scaling, ExtremeSustainedDPSRuntimeEffectScalingResult
        ):
            raise TypeError("generated runtime-state leaf scaling must be canonical when supplied")

    @property
    def complete(self) -> bool:
        upstream_complete = getattr(self.pipeline_state, "complete", False)
        if not isinstance(upstream_complete, bool):
            raise TypeError("upstream generated pipeline complete flag must be boolean")
        return upstream_complete and not self.runtime_state_choice.unresolved

    def __getattr__(self, name: str):
        return getattr(self.pipeline_state, name)


class ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService:
    """Expose static or candidate-resolved runtime families as the final search axis."""

    @staticmethod
    def _validate(frontier: ExtremeSustainedDPSRuntimeStateFrontier) -> None:
        if not isinstance(frontier, ExtremeSustainedDPSRuntimeStateFrontier):
            raise TypeError("runtime-state axis requires a canonical runtime-state frontier")
        if not frontier.denominator_proven:
            raise ValueError(
                "generated runtime-state axis requires a proven local denominator"
            )
        if frontier.unresolved:
            raise ValueError(
                "generated runtime-state axis cannot consume an unresolved runtime family"
            )
        if frontier.candidate_count <= 0 or not frontier.choices:
            raise ValueError(
                "generated runtime-state axis requires at least one runtime choice"
            )
        if frontier.candidate_count != len(frontier.choices):
            raise ValueError(
                "generated runtime-state axis candidate count does not match retained choices"
            )

    @classmethod
    def axis(
        cls,
        frontier: ExtremeSustainedDPSRuntimeStateFrontier,
    ) -> ExtremeSustainedDPSIndexedFrontierAxis:
        cls._validate(frontier)

        def candidate_count(state: object) -> int:
            complete = getattr(state, "complete", False)
            if not isinstance(complete, bool):
                raise TypeError("upstream generated pipeline complete flag must be boolean")
            if not complete:
                raise ValueError(
                    "runtime-state axis requires a complete upstream generated pipeline state"
                )
            return frontier.candidate_count

        def candidate_at(state: object, index: int):
            complete = getattr(state, "complete", False)
            if not isinstance(complete, bool):
                raise TypeError("upstream generated pipeline complete flag must be boolean")
            if not complete:
                raise ValueError(
                    "runtime-state axis requires a complete upstream generated pipeline state"
                )
            if isinstance(index, bool) or not isinstance(index, int):
                raise TypeError("generated runtime-state choice index must be an integer")
            if index < 0 or index >= frontier.candidate_count:
                raise IndexError("generated runtime-state choice index out of range")
            return ExtremeSustainedDPSGeneratedRuntimeStateLeaf(
                pipeline_state=state,
                runtime_state_choice=frontier.choices[index],
                omitted_scope=tuple(frontier.omitted_scope),
            )

        return ExtremeSustainedDPSIndexedFrontierAxis(
            "Runtime State",
            candidate_count=candidate_count,
            candidate_at=candidate_at,
            canonical_axes=("runtime_state",),
            omitted_scope=tuple(frontier.omitted_scope),
        )

    @classmethod
    def candidate_axis(
        cls,
        frontier_resolver: object,
    ) -> ExtremeSustainedDPSIndexedFrontierAxis:
        """Resolve runtime_state from each complete finalized candidate.

        The resolver may be callable or expose resolve(state). It may return either
        ExtremeSustainedDPSRuntimeStateFrontier directly or a wrapper with .frontier.
        Candidate-resolved mode is theory-closing only when every resolved frontier
        is proven, unresolved-free, and carries no omitted scope.
        """
        if frontier_resolver is None:
            raise ValueError(
                "candidate runtime-state axis requires explicit frontier resolver"
            )

        def resolve_result(state: object):
            if hasattr(frontier_resolver, "resolve"):
                result = frontier_resolver.resolve(state)
            elif callable(frontier_resolver):
                result = frontier_resolver(state)
            else:
                raise ValueError(
                    "candidate runtime-state frontier resolver is not callable"
                )
            frontier = getattr(result, "frontier", result)
            cls._validate(frontier)
            if frontier.omitted_scope:
                raise ValueError(
                    "candidate runtime-state frontier retains theoretical omitted scope: "
                    + "; ".join(frontier.omitted_scope)
                )
            relevance = getattr(result, "relevance", None)
            scaling = getattr(result, "scaling", None)
            if relevance is not None and not isinstance(
                relevance, ExtremeSustainedDPSRuntimeEffectRelevance
            ):
                raise TypeError(
                    "candidate runtime-state resolver relevance must be canonical when supplied"
                )
            if scaling is not None and not isinstance(
                scaling, ExtremeSustainedDPSRuntimeEffectScalingResult
            ):
                raise TypeError(
                    "candidate runtime-state resolver scaling must be canonical when supplied"
                )
            return result, frontier

        def resolve_frontier(state: object) -> ExtremeSustainedDPSRuntimeStateFrontier:
            return resolve_result(state)[1]

        def candidate_count(state: object) -> int:
            complete = getattr(state, "complete", False)
            if not isinstance(complete, bool):
                raise TypeError("upstream generated pipeline complete flag must be boolean")
            if not complete:
                raise ValueError(
                    "candidate runtime-state axis requires a complete upstream generated pipeline state"
                )
            return resolve_frontier(state).candidate_count

        def candidate_at(state: object, index: int):
            complete = getattr(state, "complete", False)
            if not isinstance(complete, bool):
                raise TypeError("upstream generated pipeline complete flag must be boolean")
            if not complete:
                raise ValueError(
                    "candidate runtime-state axis requires a complete upstream generated pipeline state"
                )
            result, frontier = resolve_result(state)
            if isinstance(index, bool) or not isinstance(index, int):
                raise TypeError("candidate runtime-state choice index must be an integer")
            if index < 0 or index >= frontier.candidate_count:
                raise IndexError("candidate runtime-state choice index out of range")
            return ExtremeSustainedDPSGeneratedRuntimeStateLeaf(
                pipeline_state=state,
                runtime_state_choice=frontier.choices[index],
                omitted_scope=(),
                relevance=getattr(result, "relevance", None),
                scaling=getattr(result, "scaling", None),
            )

        return ExtremeSustainedDPSIndexedFrontierAxis(
            "Runtime State",
            candidate_count=candidate_count,
            candidate_at=candidate_at,
            canonical_axes=("runtime_state",),
            omitted_scope=(),
        )

    @classmethod
    def coverage(
        cls,
        frontier: ExtremeSustainedDPSRuntimeStateFrontier,
    ) -> ExtremeSustainedDPSAxisCoverageProof:
        cls._validate(frontier)
        return ExtremeSustainedDPSAxisCoverageProof(
            source="complete caller-proven local runtime-state denominator",
            dominated_axes=("runtime_state",),
            omitted_scope=tuple(frontier.omitted_scope),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService",
    "ExtremeSustainedDPSGeneratedRuntimeStateLeaf",
]
