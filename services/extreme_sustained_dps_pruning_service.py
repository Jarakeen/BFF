from __future__ import annotations

"""Proof-safe pruning for generated sustained-DPS search frontiers.

This module does not calculate ESO damage and does not manufacture upper bounds.
It consumes optimistic bounds supplied by canonical mechanics/evaluator layers and
may prune a branch only when that proven-safe ceiling is strictly below the current
legal incumbent. Equal ceilings remain open because they can still produce a tie,
which matters to unique-leader and global-proof semantics.
"""

from dataclasses import dataclass
from enum import Enum


class ExtremeSustainedDPSPruningDisposition(str, Enum):
    PRUNED = "pruned"
    SURVIVOR = "survivor"
    FORCED_OPEN = "forced_open"


@dataclass(frozen=True)
class ExtremeSustainedDPSBoundEvidence:
    candidate_key: str
    upper_bound_dps: float | None
    proven_safe: bool
    source: str
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeSustainedDPSPruningDecision:
    candidate_key: str
    disposition: ExtremeSustainedDPSPruningDisposition
    upper_bound_dps: float | None
    incumbent_dps: float
    reason: str
    source: str
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSPruningResult:
    incumbent_dps: float
    decisions: tuple[ExtremeSustainedDPSPruningDecision, ...]
    pruned_count: int
    survivor_count: int
    forced_open_count: int
    evidence: tuple[str, ...]

    @property
    def proof_safe(self) -> bool:
        return all(
            row.disposition is not ExtremeSustainedDPSPruningDisposition.PRUNED
            or (
                row.upper_bound_dps is not None
                and row.upper_bound_dps < self.incumbent_dps - 1e-9
            )
            for row in self.decisions
        )


class ExtremeSustainedDPSPruningService:
    """Apply an incumbent only to externally proven optimistic DPS ceilings."""

    TOLERANCE = 1e-9

    @classmethod
    def prune(
        cls,
        bounds: tuple[ExtremeSustainedDPSBoundEvidence, ...],
        *,
        incumbent_dps: float,
    ) -> ExtremeSustainedDPSPruningResult:
        incumbent = float(incumbent_dps)
        if incumbent < 0:
            raise ValueError("sustained-DPS incumbent cannot be negative")

        decisions: list[ExtremeSustainedDPSPruningDecision] = []
        seen: set[str] = set()
        for evidence in tuple(bounds):
            key = str(evidence.candidate_key or "").strip()
            if not key:
                raise ValueError("sustained-DPS pruning candidate_key cannot be empty")
            if key in seen:
                raise ValueError(f"duplicate sustained-DPS pruning candidate_key: {key}")
            seen.add(key)

            source = str(evidence.source or "").strip()
            unresolved = tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in evidence.unresolved
                    if str(item).strip()
                )
            )

            if evidence.upper_bound_dps is None:
                decisions.append(
                    ExtremeSustainedDPSPruningDecision(
                        candidate_key=key,
                        disposition=ExtremeSustainedDPSPruningDisposition.FORCED_OPEN,
                        upper_bound_dps=None,
                        incumbent_dps=incumbent,
                        reason="No optimistic DPS upper bound is available; branch must remain open",
                        source=source,
                        unresolved=unresolved,
                    )
                )
                continue

            upper = float(evidence.upper_bound_dps)
            if upper < 0:
                raise ValueError(
                    f"sustained-DPS upper bound cannot be negative for candidate {key!r}"
                )

            if not bool(evidence.proven_safe):
                decisions.append(
                    ExtremeSustainedDPSPruningDecision(
                        candidate_key=key,
                        disposition=ExtremeSustainedDPSPruningDisposition.FORCED_OPEN,
                        upper_bound_dps=upper,
                        incumbent_dps=incumbent,
                        reason="Upper bound exists but is not proven pruning-safe; branch must remain open",
                        source=source,
                        unresolved=unresolved,
                    )
                )
                continue

            if upper < incumbent - cls.TOLERANCE:
                decisions.append(
                    ExtremeSustainedDPSPruningDecision(
                        candidate_key=key,
                        disposition=ExtremeSustainedDPSPruningDisposition.PRUNED,
                        upper_bound_dps=upper,
                        incumbent_dps=incumbent,
                        reason="Proven-safe optimistic ceiling is strictly below the incumbent",
                        source=source,
                        unresolved=unresolved,
                    )
                )
                continue

            decisions.append(
                ExtremeSustainedDPSPruningDecision(
                    candidate_key=key,
                    disposition=ExtremeSustainedDPSPruningDisposition.SURVIVOR,
                    upper_bound_dps=upper,
                    incumbent_dps=incumbent,
                    reason=(
                        "Optimistic ceiling can still match or exceed the incumbent; "
                        "candidate remains eligible for exact refinement/simulation"
                    ),
                    source=source,
                    unresolved=unresolved,
                )
            )

        rows = tuple(decisions)
        pruned = sum(
            row.disposition is ExtremeSustainedDPSPruningDisposition.PRUNED
            for row in rows
        )
        survivors = sum(
            row.disposition is ExtremeSustainedDPSPruningDisposition.SURVIVOR
            for row in rows
        )
        forced_open = sum(
            row.disposition is ExtremeSustainedDPSPruningDisposition.FORCED_OPEN
            for row in rows
        )
        return ExtremeSustainedDPSPruningResult(
            incumbent_dps=incumbent,
            decisions=rows,
            pruned_count=int(pruned),
            survivor_count=int(survivors),
            forced_open_count=int(forced_open),
            evidence=(
                f"Applied incumbent sustained DPS: {incumbent:g}",
                f"Pruned by proven-safe upper bound: {int(pruned)}",
                f"Survived proven-safe upper bound: {int(survivors)}",
                f"Forced open for missing/unproven bound: {int(forced_open)}",
                "Equal-to-incumbent ceilings are retained because a tie can affect leader/proof semantics",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSBoundEvidence",
    "ExtremeSustainedDPSPruningDecision",
    "ExtremeSustainedDPSPruningDisposition",
    "ExtremeSustainedDPSPruningResult",
    "ExtremeSustainedDPSPruningService",
]
