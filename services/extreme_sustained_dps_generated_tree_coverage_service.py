from __future__ import annotations

"""Promote one completed generated tree into same-tree canonical axis coverage."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedTreeCoverageResult:
    proof: ExtremeSustainedDPSAxisCoverageProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.proof, ExtremeSustainedDPSAxisCoverageProof):
            raise TypeError("generated tree coverage requires canonical axis coverage proof")
        if not isinstance(self.evidence, tuple):
            raise TypeError("generated tree coverage evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("generated tree coverage unresolved must be a tuple")
        if self.proof.unresolved != self.unresolved:
            raise ValueError(
                "generated tree coverage proof unresolved evidence must match result unresolved evidence"
            )


class ExtremeSustainedDPSGeneratedTreeCoverageService:
    """Derive coverage only from a successfully exhausted generated search tree."""

    @staticmethod
    def _tuple_field(owner: object, field: str, label: str) -> tuple:
        value = getattr(owner, field, ())
        if not isinstance(value, tuple):
            raise TypeError(f"generated tree coverage {label} must be a tuple")
        return value

    @classmethod
    def from_search(
        cls,
        *,
        search_result: object,
        axis_inventory: object,
    ) -> ExtremeSustainedDPSGeneratedTreeCoverageResult:
        global_maximum_proven = getattr(search_result, "global_maximum_proven", None)
        if not isinstance(global_maximum_proven, bool):
            raise TypeError("generated tree coverage requires boolean global_maximum_proven")
        unresolved: list[str] = []

        raw_search_unresolved = getattr(search_result, "unresolved", ())
        if not isinstance(raw_search_unresolved, tuple):
            raise TypeError("generated tree coverage search unresolved must be a tuple")
        search_unresolved = tuple(
            str(item).strip()
            for item in raw_search_unresolved
            if str(item).strip()
        )
        unresolved.extend(
            f"Generated search: {item}"
            for item in search_unresolved
        )

        finite_closed = bool(global_maximum_proven and not search_unresolved)
        if not global_maximum_proven:
            unresolved.append(
                "Generated finite search denominator maximum is not proven"
            )

        inventory_unresolved = cls._tuple_field(axis_inventory, "unresolved", "axis inventory unresolved")
        unresolved.extend(str(item) for item in inventory_unresolved if str(item))

        duplicates = cls._tuple_field(axis_inventory, "duplicate_canonical_axes", "axis inventory duplicate_canonical_axes")
        if duplicates:
            unresolved.append(
                "Generated tree contains duplicate canonical-axis enumeration: "
                + ", ".join(str(item) for item in duplicates)
            )

        complete = bool(finite_closed and not unresolved)
        searched_axes = cls._tuple_field(axis_inventory, "searched_canonical_axes", "axis inventory searched_canonical_axes")
        omitted_scope = cls._tuple_field(axis_inventory, "omitted_scope", "axis inventory omitted_scope")

        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="completed generated search tree canonical-axis inventory",
            dominated_axes=searched_axes if complete else (),
            unresolved=tuple(dict.fromkeys(unresolved)),
            omitted_scope=omitted_scope,
        )

        return ExtremeSustainedDPSGeneratedTreeCoverageResult(
            proof=proof,
            evidence=(
                f"Finite generated denominator maximum proven without unresolved search evidence: {finite_closed}",
                f"Canonical axes physically searched: {len(searched_axes)}",
                f"Canonical axes promoted from this exact tree: {len(proof.dominated_axes)}",
                f"Explicit theoretical omissions preserved from tree axes: {len(omitted_scope)}",
                "Coverage promotion uses the same completed generated tree that produced the modeled-DPS winner",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedTreeCoverageResult",
    "ExtremeSustainedDPSGeneratedTreeCoverageService",
]
