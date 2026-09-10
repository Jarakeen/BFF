from __future__ import annotations

"""Reusable proof/result contract for canonical Extreme Records.

Extreme computes the mechanical boundary.  Consumers such as Comp Maker may read
this record, compare tradeoffs, and reason about distance from the boundary, but
must not re-implement the ESO mechanics that produced it.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from services.extreme_record_objective_catalog_service import (
    ExtremeRecordObjective,
    get_extreme_record_objective,
)


class ExtremeRecordProofStatus(str, Enum):
    """How strongly the reported record value is established."""

    PROVEN = "proven"
    CONDITIONAL = "conditional"
    LOWER_BOUND = "lower_bound"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ExtremeRecordCeilingThreat:
    """One unresolved candidate that could still exceed the current winner."""

    source: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    reason: str = ""

    @property
    def bounded(self) -> bool:
        return self.lower_bound is not None and self.upper_bound is not None


@dataclass(frozen=True)
class ExtremeRecordSearchCoverage:
    """Truthful description of what the record search did and did not prove."""

    searched: tuple[str, ...] = ()
    omitted: tuple[str, ...] = ()
    candidates_screened: int | None = None
    candidates_optimized: int | None = None
    denominator_proven: bool = False

    @property
    def complete(self) -> bool:
        return self.denominator_proven and not self.omitted


@dataclass(frozen=True)
class ExtremeRecordResult:
    """Canonical Extreme Record suitable for UI and downstream optimization.

    ``raw_value`` is never replaced by a cap-adjusted value.  When the objective
    has an effective gameplay cap, ``effective_value`` and ``effective_cap``
    describe that interpretation separately so Extreme can preserve gloriously
    pointless overcap records without misleading Comp Maker about usable value.

    ``winning_build`` intentionally remains an opaque snapshot payload here.  The
    producing optimizer owns its concrete build type/serialization; this contract
    only promises to preserve that snapshot for consumers.
    """

    objective: ExtremeRecordObjective
    raw_value: float | None
    proof_status: ExtremeRecordProofStatus
    winning_build: Any | None = None
    effective_value: float | None = None
    effective_cap: float | None = None
    unit: str = ""
    runtime_prerequisites: tuple[str, ...] = ()
    self_provided_conditions: tuple[str, ...] = ()
    external_conditions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    ceiling_threats: tuple[ExtremeRecordCeilingThreat, ...] = ()
    search_coverage: ExtremeRecordSearchCoverage = ExtremeRecordSearchCoverage()
    explanation: tuple[str, ...] = ()

    @property
    def objective_key(self) -> str:
        return self.objective.key

    @property
    def globally_proven(self) -> bool:
        return (
            self.proof_status is ExtremeRecordProofStatus.PROVEN
            and self.raw_value is not None
            and self.search_coverage.complete
            and not self.unresolved
            and not self.ceiling_threats
        )

    @property
    def conditionally_achievable(self) -> bool:
        return (
            self.proof_status is ExtremeRecordProofStatus.CONDITIONAL
            and self.raw_value is not None
            and not self.unresolved
        )

    @property
    def has_effective_cap_interpretation(self) -> bool:
        return self.effective_value is not None or self.effective_cap is not None

    @classmethod
    def for_objective(
        cls,
        objective_key: str,
        *,
        raw_value: float | None,
        proof_status: ExtremeRecordProofStatus | str,
        **kwargs,
    ) -> "ExtremeRecordResult":
        objective = get_extreme_record_objective(objective_key)
        try:
            status = (
                proof_status
                if isinstance(proof_status, ExtremeRecordProofStatus)
                else ExtremeRecordProofStatus(str(proof_status).strip().casefold())
            )
        except ValueError as exc:
            raise ValueError(f"Unsupported Extreme Record proof status: {proof_status!r}") from exc
        return cls(
            objective=objective,
            raw_value=None if raw_value is None else float(raw_value),
            proof_status=status,
            **kwargs,
        )
