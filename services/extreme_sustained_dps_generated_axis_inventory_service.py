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

    def __post_init__(self) -> None:
        for name in (
            "axis_names",
            "searched_canonical_axes",
            "missing_canonical_axes",
            "untagged_axis_names",
            "duplicate_canonical_axes",
            "omitted_scope",
            "evidence",
            "unresolved",
        ):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"generated axis inventory {name} must be a tuple")
        canonical = tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES)
        searched = tuple(self.searched_canonical_axes)
        if any(axis not in canonical for axis in searched):
            raise ValueError("generated axis inventory searched axes must be canonical")
        expected_missing = tuple(axis for axis in canonical if axis not in set(searched))
        if self.missing_canonical_axes != expected_missing:
            raise ValueError(
                "generated axis inventory missing_canonical_axes must match canonical minus searched axes"
            )
        if any(axis not in searched for axis in self.duplicate_canonical_axes):
            raise ValueError(
                "generated axis inventory duplicate axes must also be searched axes"
            )
        if len(set(searched)) != len(searched):
            raise ValueError("generated axis inventory searched axes must be unique")
        if len(set(self.axis_names)) != len(self.axis_names):
            raise ValueError("generated axis inventory axis_names must be unique")
        if any(name not in set(self.axis_names) for name in self.untagged_axis_names):
            raise ValueError(
                "generated axis inventory untagged_axis_names must come from axis_names"
            )
        if self.duplicate_canonical_axes and not self.unresolved:
            raise ValueError(
                "generated axis inventory duplicate canonical axes require unresolved evidence"
            )
        if self.missing_canonical_axes and not all(
            axis not in searched for axis in self.missing_canonical_axes
        ):
            raise ValueError(
                "generated axis inventory missing axes cannot also be searched"
            )


class ExtremeSustainedDPSGeneratedAxisInventoryService:
    """Report tree shape only; denominator proof remains owned by frontier services."""

    @classmethod
    def inventory(
        cls,
        axes: tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...],
        *,
        additional_canonical_axes: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSGeneratedAxisInventory:
        if not isinstance(axes, tuple):
            raise TypeError("generated axis inventory axes must be a tuple")
        if not isinstance(additional_canonical_axes, tuple):
            raise TypeError("generated axis inventory additional_canonical_axes must be a tuple")

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
            for raw_token in axis.canonical_axes:
                token = str(raw_token or "").strip()
                if token not in canonical_set:
                    unresolved.append(
                        f"Generated tree axis {axis.name!r} declares non-canonical mutation axis: "
                        f"{token or '(empty)'}"
                    )
                    continue
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
