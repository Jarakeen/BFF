from __future__ import annotations

"""Lazy indexed-frontier wiring for generated sustained-DPS branch-and-bound search.

The concrete Extreme frontiers already know how to count and materialize one candidate
at an index. This service gives those authorities one common tree shape without
materializing their Cartesian product. It owns coordinate identity and orchestration
only; frontier legality, optimistic ceilings, and exact combat evaluation remain
caller-supplied canonical authorities.
"""

from dataclasses import dataclass
from typing import Callable, Protocol

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
    ExtremeSustainedDPSGeneratedBranchAndBoundSearchService,
    ExtremeSustainedDPSGeneratedSearchBranch,
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_partial_branch_upper_bound_service import (
    ExtremeSustainedDPSBoundEnvelopeInput,
    ExtremeSustainedDPSPartialBranchUpperBoundService,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


BoundInputProvider = Callable[
    [object],
    tuple[ExtremeSustainedDPSBoundEnvelopeInput, ...],
]


@dataclass(frozen=True)
class ExtremeSustainedDPSIndexedFrontierAxis:
    name: str
    candidate_count: Callable[[object], int]
    candidate_at: Callable[[object, int], object]
    bound_inputs: BoundInputProvider | None = None

    def __post_init__(self) -> None:
        name = " ".join(str(self.name or "").strip().split())
        if not name:
            raise ValueError("generated sustained-DPS frontier axis requires a name")
        if not callable(self.candidate_count):
            raise TypeError("generated frontier axis candidate_count must be callable")
        if not callable(self.candidate_at):
            raise TypeError("generated frontier axis candidate_at must be callable")
        if self.bound_inputs is not None and not callable(self.bound_inputs):
            raise TypeError("generated frontier axis bound_inputs must be callable")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedFrontierNode:
    candidate_key: str
    state: object
    coordinates: tuple[tuple[str, int], ...]
    evidence: tuple[str, ...] = ()

    @property
    def depth(self) -> int:
        return len(self.coordinates)


class ExtremeSustainedDPSGeneratedFrontierLeafEvaluator(Protocol):
    def __call__(
        self,
        node: ExtremeSustainedDPSGeneratedFrontierNode,
    ) -> ExtremeSustainedDPSExactLeafEvaluation: ...


class ExtremeSustainedDPSGeneratedFrontierWiringService:
    """Expose indexed Extreme frontiers as one lazy branch-and-bound tree."""

    @staticmethod
    def _axis_key(name: str) -> str:
        key = "-".join(
            part
            for part in "".join(
                character.casefold()
                if character.isalnum()
                else " "
                for character in str(name or "")
            ).split()
            if part
        )
        if not key:
            raise ValueError("generated sustained-DPS frontier axis key is empty")
        return key

    @classmethod
    def _validate_axes(
        cls,
        axes: tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...],
    ) -> None:
        seen: set[str] = set()
        for axis in axes:
            key = cls._axis_key(axis.name)
            if key in seen:
                raise ValueError(
                    f"duplicate generated sustained-DPS frontier axis identity: {axis.name}"
                )
            seen.add(key)

    @staticmethod
    def _bound_inputs(
        provider: BoundInputProvider | None,
        state: object,
    ) -> tuple[ExtremeSustainedDPSBoundEnvelopeInput, ...]:
        if provider is None:
            return ()
        return tuple(provider(state))

    @classmethod
    def search(
        cls,
        root_state: object,
        *,
        axes: tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...],
        evaluate_leaf: ExtremeSustainedDPSGeneratedFrontierLeafEvaluator,
        required_duration_seconds: float,
        root_key: str = "generated-root",
        root_bound_inputs: BoundInputProvider | None = None,
    ) -> ExtremeSustainedDPSGeneratedSearchResult:
        cls._validate_axes(axes)
        key = str(root_key or "").strip()
        if not key:
            raise ValueError("generated sustained-DPS frontier root_key cannot be empty")

        root_node = ExtremeSustainedDPSGeneratedFrontierNode(
            candidate_key=key,
            state=root_state,
            coordinates=(),
            evidence=("Generated frontier root",),
        )
        root_envelope = ExtremeSustainedDPSPartialBranchUpperBoundService.compose(
            key,
            cls._bound_inputs(root_bound_inputs, root_state),
        )
        root = ExtremeSustainedDPSGeneratedSearchBranch(
            candidate_key=key,
            depth=0,
            is_leaf=not axes,
            upper_bound=root_envelope.bound,
            payload=root_node,
        )

        def expand_branch(
            branch: ExtremeSustainedDPSGeneratedSearchBranch,
        ) -> tuple[ExtremeSustainedDPSGeneratedSearchBranch, ...]:
            node = branch.payload
            if not isinstance(node, ExtremeSustainedDPSGeneratedFrontierNode):
                raise TypeError("generated frontier branch payload has wrong type")
            axis_index = int(branch.depth)
            if axis_index >= len(axes):
                return ()

            axis = axes[axis_index]
            count = int(axis.candidate_count(node.state))
            if count < 0:
                raise ValueError(
                    f"generated frontier axis {axis.name!r} returned a negative candidate count"
                )

            children: list[ExtremeSustainedDPSGeneratedSearchBranch] = []
            axis_key = cls._axis_key(axis.name)
            for candidate_index in range(count):
                state = axis.candidate_at(node.state, candidate_index)
                child_key = f"{node.candidate_key}|{axis_key}:{candidate_index}"
                coordinates = (*node.coordinates, (axis.name, candidate_index))
                child_node = ExtremeSustainedDPSGeneratedFrontierNode(
                    candidate_key=child_key,
                    state=state,
                    coordinates=coordinates,
                    evidence=(
                        *node.evidence,
                        f"{axis.name} candidate {candidate_index + 1} of {count}",
                    ),
                )
                envelope = ExtremeSustainedDPSPartialBranchUpperBoundService.compose(
                    child_key,
                    cls._bound_inputs(axis.bound_inputs, state),
                    inherited_parent_bound=branch.upper_bound,
                )
                children.append(
                    ExtremeSustainedDPSGeneratedSearchBranch(
                        candidate_key=child_key,
                        depth=axis_index + 1,
                        is_leaf=axis_index + 1 == len(axes),
                        upper_bound=envelope.bound,
                        payload=child_node,
                    )
                )
            return tuple(children)

        def exact_leaf(
            branch: ExtremeSustainedDPSGeneratedSearchBranch,
        ) -> ExtremeSustainedDPSExactLeafEvaluation:
            node = branch.payload
            if not isinstance(node, ExtremeSustainedDPSGeneratedFrontierNode):
                raise TypeError("generated frontier leaf payload has wrong type")
            result = evaluate_leaf(node)
            if result.candidate_key != node.candidate_key:
                return ExtremeSustainedDPSExactLeafEvaluation(
                    candidate_key=node.candidate_key,
                    modeled_dps=None,
                    duration_seconds=result.duration_seconds,
                    mechanic_complete=False,
                    evidence=tuple(result.evidence),
                    unresolved=(
                        *tuple(result.unresolved),
                        "Generated frontier leaf evaluator returned a mismatched candidate identity",
                    ),
                )
            return result

        return ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
            (root,),
            expand_branch=expand_branch,
            evaluate_leaf=exact_leaf,
            required_duration_seconds=required_duration_seconds,
        )


__all__ = [
    "BoundInputProvider",
    "ExtremeSustainedDPSGeneratedFrontierLeafEvaluator",
    "ExtremeSustainedDPSGeneratedFrontierNode",
    "ExtremeSustainedDPSGeneratedFrontierWiringService",
    "ExtremeSustainedDPSIndexedFrontierAxis",
]
