from __future__ import annotations

"""Promote only proven sustained-DPS structural denominator coverage.

The structural frontier currently also enumerates an active-bar coordinate inherited
from the objective-neutral Extreme universe. Sustained-DPS rotation search already owns
starting-bar route semantics, so this adapter deliberately promotes only race,
class-route, and attribute coverage. It does not claim that the structural frontier is
already wired into the generated pipeline.
"""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSGeneratedFrontier,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSStructuralAxisCoverageResult:
    proof: ExtremeSustainedDPSAxisCoverageProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSStructuralAxisCoverageService:
    """Adapt structural denominator proof without overstating search integration."""

    @classmethod
    def from_frontier(
        cls,
        frontier: ExtremeSustainedDPSGeneratedFrontier,
    ) -> ExtremeSustainedDPSStructuralAxisCoverageResult:
        unresolved = list(frontier.unresolved)
        complete = bool(
            frontier.structural_denominator_proven
            and frontier.structural_candidate_count > 0
            and not unresolved
        )

        expanded = tuple(str(item).strip() for item in frontier.expanded_axes)
        expected = {
            "race",
            "legal class route",
            "64-point attribute allocation",
            "active bar",
        }
        missing_expected = tuple(
            item
            for item in sorted(expected, key=str.casefold)
            if item not in set(expanded)
        )
        if missing_expected:
            unresolved.append(
                "Sustained-DPS structural frontier is missing expected structural coordinate(s): "
                + ", ".join(missing_expected)
            )
            complete = False

        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete sustained-DPS structural race/class/attribute denominator",
            dominated_axes=(
                ("race", "class_route", "attributes")
                if complete
                else ()
            ),
            unresolved=tuple(unresolved),
        )

        return ExtremeSustainedDPSStructuralAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Structural candidate coordinates retained: {frontier.structural_candidate_count}",
                (
                    "Canonical structural coverage promoted: race + class_route + attributes"
                    if complete
                    else "Canonical structural coverage withheld"
                ),
                "The frontier's active-bar coordinate is not promoted as a canonical Objective #32 axis",
                "This coverage proves structural enumeration only; it does not prove those coordinates are wired into the generated search tree",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeSustainedDPSStructuralAxisCoverageResult",
    "ExtremeSustainedDPSStructuralAxisCoverageService",
]
