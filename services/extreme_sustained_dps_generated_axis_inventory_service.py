from __future__ import annotations

"""Inventory canonical mutation axes physically represented in a generated search tree."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedAxisInventory:
    axis_names: tuple[str, ...]
    searched_canonical_axes: tuple[str, ...]
    missing_canonical_axes: tuple[str, ...]
    untagged_axis_names: tuple[str, ...]
    duplicate_canonical_axes: tuple[str, ...]
    omitted_scope: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSGeneratedAxisInventoryService:
    """Report tree shape only; denominator proof remains owned by frontier services."""

    @classmethod
    def inventory(
        cls,
        axes: tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...],
        *,
        additional_canonical_axes: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSGeneratedAxisInventory:
        canonical = tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES)
        canonical_set = set(canonical)
        axis_names = tuple(axis.name for axis in axes)

        untagged = tuple(
            axis.name
            for axis in axes
            if not axis.canonical_axes
        )

        occurrences: dict[str, int] = {}
        searched: list[str] = []
        unresolved: list[str] = []
        omitted_scope: list[str] = []

        for raw in additional_canonical_axes:
            token = str(raw or "").strip()
            if token not in canonical_set:
                unresolved.append(
                    f"Additional generated tree axis is not canonical: {token or '(empty)'}"
                )
                continue
            occurrences[token] = occurrences.get(token, 0) + 1
            if token not in searched:
                searched.append(token)

        for axis in axes:
            omitted_scope.extend(axis.omitted_scope)
            for token in axis.canonical_axes:
                occurrences[token] = occurrences.get(token, 0) + 1
                if token not in searched:
                    searched.append(token)

        duplicates = tuple(
            axis
            for axis in canonical
            if occurrences.get(axis, 0) > 1
        )
        if duplicates:
            unresolved.append(
                "Generated tree enumerates canonical mutation axis more than once: "
                + ", ".join(duplicates)
            )

        missing = tuple(
            axis
            for axis in canonical
            if axis not in set(searched)
        )

        return ExtremeSustainedDPSGeneratedAxisInventory(
            axis_names=axis_names,
            searched_canonical_axes=tuple(
                axis for axis in canonical if axis in set(searched)
            ),
            missing_canonical_axes=missing,
            untagged_axis_names=untagged,
            duplicate_canonical_axes=duplicates,
            omitted_scope=tuple(dict.fromkeys(omitted_scope)),
            evidence=(
                f"Generated indexed axes inspected: {len(axes)}",
                f"Canonical mutation axes physically enumerated: {len(set(searched))}",
                f"Canonical mutation axes not physically enumerated: {len(missing)}",
                f"Untagged generated axes: {len(untagged)}",
                f"Explicit theoretical omitted-scope items carried by axes: {len(tuple(dict.fromkeys(omitted_scope)))}",
                "Tree-axis inventory is structural evidence only; it does not prove any frontier denominator complete",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedAxisInventory",
    "ExtremeSustainedDPSGeneratedAxisInventoryService",
]
