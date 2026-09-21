from __future__ import annotations

"""Proof-safe optimistic ceiling composition for partial generated DPS branches.

Multiple independent optimistic ceilings for the same branch are intersected by taking
the minimum proven-safe numeric ceiling. This is safe because every accepted input is
already an upper bound on the same branch objective. Numeric contributions are never
summed here, avoiding double-counting across overlapping mechanics/stat authorities.

A child branch may inherit any proven-safe parent ceiling and tighten it with
child-specific evidence. Missing or unproven local evidence cannot weaken an already
proven inherited ceiling, but is preserved as informational evidence.
"""

from dataclasses import dataclass
from math import isfinite

from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSBoundEnvelopeInput:
    label: str
    evidence: ExtremeSustainedDPSBoundEvidence


@dataclass(frozen=True)
class ExtremeSustainedDPSBoundEnvelope:
    candidate_key: str
    bound: ExtremeSustainedDPSBoundEvidence
    accepted_sources: tuple[str, ...]
    rejected_sources: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSPartialBranchUpperBoundService:
    """Intersect externally proven ceilings without manufacturing new mechanics."""

    @classmethod
    def compose(
        cls,
        candidate_key: str,
        inputs: tuple[ExtremeSustainedDPSBoundEnvelopeInput, ...],
        *,
        inherited_parent_bound: ExtremeSustainedDPSBoundEvidence | None = None,
    ) -> ExtremeSustainedDPSBoundEnvelope:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("partial-branch upper-bound composition requires candidate_key")

        rows = list(inputs)
        if inherited_parent_bound is not None:
            rows.insert(
                0,
                ExtremeSustainedDPSBoundEnvelopeInput(
                    label="inherited parent bound",
                    evidence=inherited_parent_bound,
                ),
            )

        accepted: list[tuple[str, ExtremeSustainedDPSBoundEvidence]] = []
        rejected: list[str] = []
        unresolved: list[str] = []

        for row in rows:
            label = str(row.label or "").strip() or "unnamed bound source"
            evidence = row.evidence

            if evidence.upper_bound_dps is None:
                rejected.append(f"{label}: no numeric upper bound")
                unresolved.extend(
                    f"{label}: {item}"
                    for item in evidence.unresolved
                )
                continue

            value = float(evidence.upper_bound_dps)
            if not isfinite(value) or value < 0.0:
                raise ValueError(
                    f"{label}: sustained-DPS upper bound must be finite and non-negative"
                )

            if not bool(evidence.proven_safe):
                rejected.append(f"{label}: numeric bound is not proven safe")
                unresolved.extend(
                    f"{label}: {item}"
                    for item in evidence.unresolved
                )
                continue

            accepted.append((label, evidence))

        if accepted:
            winning_label, winning = min(
                accepted,
                key=lambda item: (
                    float(item[1].upper_bound_dps),
                    item[0].casefold(),
                ),
            )
            upper = float(winning.upper_bound_dps)
            source = (
                "proof-safe partial-branch upper-bound envelope; tightest source: "
                + winning_label
            )
            bound = ExtremeSustainedDPSBoundEvidence(
                candidate_key=key,
                upper_bound_dps=upper,
                proven_safe=True,
                source=source,
                unresolved=(),
            )
        else:
            bound = ExtremeSustainedDPSBoundEvidence(
                candidate_key=key,
                upper_bound_dps=None,
                proven_safe=False,
                source="no proven-safe partial-branch upper bound available",
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        accepted_sources = tuple(label for label, _row in accepted)
        rejected_sources = tuple(rejected)
        return ExtremeSustainedDPSBoundEnvelope(
            candidate_key=key,
            bound=bound,
            accepted_sources=accepted_sources,
            rejected_sources=rejected_sources,
            evidence=(
                f"Candidate branch: {key}",
                f"Proven-safe ceiling sources accepted: {len(accepted_sources)}",
                f"Missing/unproven ceiling sources ignored for pruning: {len(rejected_sources)}",
                (
                    f"Tightest proven-safe optimistic DPS ceiling: {bound.upper_bound_dps:g}"
                    if bound.upper_bound_dps is not None
                    else "Tightest proven-safe optimistic DPS ceiling: unavailable"
                ),
                "Safe branch ceilings are intersected with min(); overlapping mechanics are never added together",
                "A proven-safe parent ceiling remains valid for every child subset and may be tightened by child-specific proof",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeSustainedDPSBoundEnvelope",
    "ExtremeSustainedDPSBoundEnvelopeInput",
    "ExtremeSustainedDPSPartialBranchUpperBoundService",
]
