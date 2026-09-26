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

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
)
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
    canonical_axes: tuple[str, ...] = ()
    omitted_scope: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("generated sustained-DPS frontier axis name must be a string")
        if not isinstance(self.canonical_axes, tuple):
            raise TypeError("generated frontier axis canonical_axes must be a tuple")
        if not isinstance(self.omitted_scope, tuple):
            raise TypeError("generated frontier axis omitted_scope must be a tuple")
        name = " ".join(self.name.strip().split())
        if not name:
            raise ValueError("generated sustained-DPS frontier axis requires a name")
        if not callable(self.candidate_count):
            raise TypeError("generated frontier axis candidate_count must be callable")
        if not callable(self.candidate_at):
            raise TypeError("generated frontier axis candidate_at must be callable")
        if self.bound_inputs is not None and not callable(self.bound_inputs):
            raise TypeError("generated frontier axis bound_inputs must be callable")
        canonical = {
            axis.casefold(): axis
            for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        }
        normalized_axes: list[str] = []
        unknown: list[str] = []
        for raw in self.canonical_axes:
            if not isinstance(raw, str):
                raise TypeError("generated frontier axis canonical_axes must contain strings")
            token = raw.strip().casefold()
            if not token:
                continue
            axis = canonical.get(token)
            if axis is None:
                unknown.append(str(raw).strip())
            elif axis not in normalized_axes:
                normalized_axes.append(axis)
        if unknown:
            raise ValueError(
                "generated frontier axis declares unknown canonical mutation axis: "
                + ", ".join(sorted(set(unknown), key=str.casefold))
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "canonical_axes", tuple(normalized_axes))
        object.__setattr__(
            self,
            "omitted_scope",
            tuple(
                dict.fromkeys(
                    item.strip()
                    for item in self.omitted_scope
                    if isinstance(item, str) and item.strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedFrontierNode:
    candidate_key: str
    state: object
    coordinates: tuple[tuple[str, int], ...]
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_key = str(self.candidate_key or "").strip()
        if not candidate_key:
            raise ValueError("generated frontier node requires candidate_key")

        normalized_coordinates: list[tuple[str, int]] = []
        for row in self.coordinates:
            if not isinstance(row, tuple) or len(row) != 2:
                raise TypeError(
                    "generated frontier node coordinates must contain (axis_name, index) pairs"
                )
            if not isinstance(row[0], str):
                raise TypeError("generated frontier node coordinate axis name must be a string")
            axis_name = " ".join(row[0].strip().split())
            index = row[1]
            if not axis_name:
                raise ValueError(
                    "generated frontier node coordinate axis name cannot be empty"
                )
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise ValueError(
                    "generated frontier node coordinate index must be a non-negative integer"
                )
            normalized_coordinates.append((axis_name, index))

        evidence = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.evidence
                if str(item).strip()
            )
        )
        object.__setattr__(self, "candidate_key", candidate_key)
        object.__setattr__(self, "coordinates", tuple(normalized_coordinates))
        object.__setattr__(self, "evidence", evidence)

    @property
    def depth(self) -> int:
        return len(self.coordinates)


NodeBoundInputProvider = Callable[
    [ExtremeSustainedDPSGeneratedFrontierNode],
    tuple[ExtremeSustainedDPSBoundEnvelopeInput, ...],
]


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
        if not isinstance(axes, tuple):
            raise TypeError("generated sustained-DPS frontier axes must be a tuple")
        if any(not isinstance(axis, ExtremeSustainedDPSIndexedFrontierAxis) for axis in axes):
            raise TypeError("generated sustained-DPS frontier axes must contain indexed frontier axes")
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
        result = provider(state)
        if not isinstance(result, tuple):
            raise TypeError("generated frontier bound provider must return a tuple")
        return result

    @staticmethod
    def _node_bound_inputs(
        provider: NodeBoundInputProvider | None,
        node: ExtremeSustainedDPSGeneratedFrontierNode,
    ) -> tuple[ExtremeSustainedDPSBoundEnvelopeInput, ...]:
        if provider is None:
            return ()
        result = provider(node)
        if not isinstance(result, tuple):
            raise TypeError("generated frontier node-bound provider must return a tuple")
        return result

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
        branch_bound_inputs: NodeBoundInputProvider | None = None,
    ) -> ExtremeSustainedDPSGeneratedSearchResult:
        cls._validate_axes(axes)
        if not isinstance(root_key, str):
            raise TypeError("generated sustained-DPS frontier root_key must be a string")
        key = root_key.strip()
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
            (
                *cls._bound_inputs(root_bound_inputs, root_state),
                *cls._node_bound_inputs(branch_bound_inputs, root_node),
            ),
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
            raw_count = axis.candidate_count(node.state)
            if isinstance(raw_count, bool) or not isinstance(raw_count, int):
                raise TypeError(
                    f"generated frontier axis {axis.name!r} candidate count must be an integer"
                )
            count = raw_count
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
                    (
                        *cls._bound_inputs(axis.bound_inputs, state),
                        *cls._node_bound_inputs(branch_bound_inputs, child_node),
                    ),
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
            if not isinstance(result, ExtremeSustainedDPSExactLeafEvaluation):
                raise TypeError("generated frontier leaf evaluator must return canonical exact evidence")
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
    "NodeBoundInputProvider",
    "ExtremeSustainedDPSGeneratedFrontierLeafEvaluator",
    "ExtremeSustainedDPSGeneratedFrontierNode",
    "ExtremeSustainedDPSGeneratedFrontierWiringService",
    "ExtremeSustainedDPSIndexedFrontierAxis",
]
