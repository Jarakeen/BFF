from __future__ import annotations

"""Append one proven local runtime-state family to generated sustained-DPS search."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
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

    @property
    def complete(self) -> bool:
        return bool(
            getattr(self.pipeline_state, "complete", False)
            and not self.runtime_state_choice.unresolved
        )

    def __getattr__(self, name: str):
        return getattr(self.pipeline_state, name)


class ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService:
    """Expose a locally closed runtime family as one final indexed search axis."""

    @staticmethod
    def _validate(frontier: ExtremeSustainedDPSRuntimeStateFrontier) -> None:
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
            if not bool(getattr(state, "complete", False)):
                raise ValueError(
                    "runtime-state axis requires a complete upstream generated pipeline state"
                )
            return int(frontier.candidate_count)

        def candidate_at(state: object, index: int):
            if not bool(getattr(state, "complete", False)):
                raise ValueError(
                    "runtime-state axis requires a complete upstream generated pipeline state"
                )
            target = int(index)
            if target < 0 or target >= frontier.candidate_count:
                raise IndexError("generated runtime-state choice index out of range")
            return ExtremeSustainedDPSGeneratedRuntimeStateLeaf(
                pipeline_state=state,
                runtime_state_choice=frontier.choices[target],
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
