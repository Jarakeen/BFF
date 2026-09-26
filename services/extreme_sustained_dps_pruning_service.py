from __future__ import annotations

"""Proof-safe pruning for generated sustained-DPS search frontiers.

This module does not calculate ESO damage and does not manufacture upper bounds.
It consumes optimistic bounds supplied by canonical mechanics/evaluator layers and
may prune a branch only when that proven-safe ceiling is strictly below the current
legal incumbent. Equal ceilings remain open because they can still produce a tie,
which matters to unique-leader and global-proof semantics.
"""

from dataclasses import dataclass
import math
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

    def __post_init__(self) -> None:
        key = str(self.candidate_key or "").strip()
        source = str(self.source or "").strip()
        if not key:
            raise ValueError("sustained-DPS bound evidence requires candidate_key")
        if not source:
            raise ValueError("sustained-DPS bound evidence requires source")
        if not isinstance(self.proven_safe, bool):
            raise TypeError("sustained-DPS bound proven_safe must be boolean")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("sustained-DPS bound unresolved must be a tuple")

        upper = self.upper_bound_dps
        if upper is not None:
            if isinstance(upper, bool):
                raise TypeError("sustained-DPS upper bound must be numeric")
            try:
                upper = float(upper)
            except (TypeError, ValueError):
                raise TypeError("sustained-DPS upper bound must be numeric") from None
            if not math.isfinite(upper) or upper < 0.0:
                raise ValueError(
                    "sustained-DPS upper bound must be finite and non-negative"
                )
        elif self.proven_safe:
            raise ValueError(
                "sustained-DPS bound cannot be proven safe when no upper bound is available"
            )

        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.unresolved
                if str(item).strip()
            )
        )
        object.__setattr__(self, "candidate_key", key)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "upper_bound_dps", upper)
        object.__setattr__(self, "unresolved", unresolved)


@dataclass(frozen=True)
class ExtremeSustainedDPSPruningDecision:
    candidate_key: str
    disposition: ExtremeSustainedDPSPruningDisposition
    upper_bound_dps: float | None
    incumbent_dps: float
    reason: str
    source: str
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        key = str(self.candidate_key or "").strip()
        reason = str(self.reason or "").strip()
        source = str(self.source or "").strip()
        if not key:
            raise ValueError("pruning decision requires candidate_key")
        if not isinstance(self.disposition, ExtremeSustainedDPSPruningDisposition):
            raise TypeError("pruning decision disposition must be canonical pruning disposition")
        if not reason:
            raise ValueError("pruning decision requires reason")
        if not source:
            raise ValueError("pruning decision requires source")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("pruning decision unresolved must be a tuple")

        incumbent = self.incumbent_dps
        if isinstance(incumbent, bool):
            raise TypeError("pruning decision incumbent_dps must be numeric")
        try:
            incumbent = float(incumbent)
        except (TypeError, ValueError):
            raise TypeError("pruning decision incumbent_dps must be numeric") from None
        if not math.isfinite(incumbent) or incumbent < 0.0:
            raise ValueError("pruning decision incumbent_dps must be finite and non-negative")

        upper = self.upper_bound_dps
        if upper is not None:
            if isinstance(upper, bool):
                raise TypeError("pruning decision upper_bound_dps must be numeric")
            try:
                upper = float(upper)
            except (TypeError, ValueError):
                raise TypeError("pruning decision upper_bound_dps must be numeric") from None
            if not math.isfinite(upper) or upper < 0.0:
                raise ValueError(
                    "pruning decision upper_bound_dps must be finite and non-negative"
                )

        if self.disposition is ExtremeSustainedDPSPruningDisposition.PRUNED:
            if upper is None or upper >= incumbent - 1e-9:
                raise ValueError(
                    "pruned decision requires upper bound strictly below incumbent"
                )
        elif self.disposition is ExtremeSustainedDPSPruningDisposition.SURVIVOR:
            if upper is None:
                raise ValueError("survivor pruning decision requires numeric upper bound")

        object.__setattr__(self, "candidate_key", key)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "incumbent_dps", incumbent)
        object.__setattr__(self, "upper_bound_dps", upper)
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSPruningResult:
    incumbent_dps: float
    decisions: tuple[ExtremeSustainedDPSPruningDecision, ...]
    pruned_count: int
    survivor_count: int
    forced_open_count: int
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.incumbent_dps, bool):
            raise TypeError("pruning result incumbent_dps must be numeric")
        incumbent = float(self.incumbent_dps)
        if not math.isfinite(incumbent) or incumbent < 0.0:
            raise ValueError("pruning result incumbent_dps must be finite and non-negative")
        if not isinstance(self.decisions, tuple):
            raise TypeError("pruning result decisions must be a tuple")
        if not isinstance(self.evidence, tuple):
            raise TypeError("pruning result evidence must be a tuple")
        if any(
            not isinstance(row, ExtremeSustainedDPSPruningDecision)
            for row in self.decisions
        ):
            raise TypeError(
                "pruning result decisions must contain canonical pruning decisions"
            )
        counts = {
            "pruned_count": self.pruned_count,
            "survivor_count": self.survivor_count,
            "forced_open_count": self.forced_open_count,
        }
        for label, value in counts.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"pruning result {label} must be a non-negative integer")

        expected = {
            "pruned_count": sum(
                row.disposition is ExtremeSustainedDPSPruningDisposition.PRUNED
                for row in self.decisions
            ),
            "survivor_count": sum(
                row.disposition is ExtremeSustainedDPSPruningDisposition.SURVIVOR
                for row in self.decisions
            ),
            "forced_open_count": sum(
                row.disposition is ExtremeSustainedDPSPruningDisposition.FORCED_OPEN
                for row in self.decisions
            ),
        }
        for label, expected_value in expected.items():
            if counts[label] != expected_value:
                raise ValueError(
                    f"pruning result {label} must match decision dispositions"
                )

        object.__setattr__(self, "incumbent_dps", incumbent)
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(
            self,
            "evidence",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.evidence
                    if str(item).strip()
                )
            ),
        )

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
        if not isinstance(bounds, tuple):
            raise TypeError("sustained-DPS pruning bounds must be a tuple")
        if any(not isinstance(bound, ExtremeSustainedDPSBoundEvidence) for bound in bounds):
            raise TypeError("sustained-DPS pruning bounds must contain canonical bound evidence")
        if isinstance(incumbent_dps, bool):
            raise TypeError("sustained-DPS incumbent must be numeric")
        try:
            incumbent = float(incumbent_dps)
        except (TypeError, ValueError):
            raise TypeError("sustained-DPS incumbent must be numeric") from None
        if not math.isfinite(incumbent) or incumbent < 0:
            raise ValueError(
                "sustained-DPS incumbent must be finite and non-negative"
            )

        decisions: list[ExtremeSustainedDPSPruningDecision] = []
        seen: set[str] = set()
        for evidence in bounds:
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

            if evidence.proven_safe is not True:
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
