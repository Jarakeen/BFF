from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.canonical_knowledge_gap import (
    CanonicalKnowledgeDomain,
    CanonicalKnowledgeGap,
)


class CanonicalMechanicsCoverageStatus(str, Enum):
    """How completely one mechanics area can support decisions today."""

    CALCULATION_READY = "calculation_ready"
    PARTIAL = "partial"
    MISSING_CRITICAL = "missing_critical"
    NICHE = "niche"


@dataclass(frozen=True)
class CanonicalMechanicsCoverageEvidence:
    """One evidence-backed statement about shared mechanics coverage.

    Coverage metadata is deliberately separate from ESO mechanics themselves. It
    records what BFF can currently prove, where that proof lives, and what additional
    evidence would broaden Comp Maker, Rotation Maker, and/or Optimizer decisions.
    """

    domain: CanonicalKnowledgeDomain
    key: str
    status: CanonicalMechanicsCoverageStatus
    capability: str
    evidence_source: str
    consumers: tuple[str, ...]
    missing_evidence: str | None = None
    research_context: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("key", "capability", "evidence_source"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"canonical mechanics coverage {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)

        normalized_consumers: list[str] = []
        seen: set[str] = set()
        for consumer in self.consumers:
            value = str(consumer or "").strip().casefold()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_consumers.append(value)
        if not normalized_consumers:
            raise ValueError("canonical mechanics coverage requires at least one consumer")
        object.__setattr__(self, "consumers", tuple(normalized_consumers))

        if self.missing_evidence is not None:
            value = str(self.missing_evidence or "").strip()
            object.__setattr__(self, "missing_evidence", value or None)
        if self.research_context is not None:
            value = str(self.research_context or "").strip()
            object.__setattr__(self, "research_context", value or None)

        if (
            self.status
            in (
                CanonicalMechanicsCoverageStatus.PARTIAL,
                CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
            )
            and not self.missing_evidence
        ):
            raise ValueError(
                "partial or missing-critical canonical mechanics coverage requires missing_evidence"
            )


@dataclass(frozen=True)
class CanonicalMechanicsCoverageReport:
    rows: tuple[CanonicalMechanicsCoverageEvidence, ...]
    knowledge_gaps: tuple[CanonicalKnowledgeGap, ...]

    def rows_for(self, consumer: str) -> tuple[CanonicalMechanicsCoverageEvidence, ...]:
        key = str(consumer or "").strip().casefold()
        return tuple(row for row in self.rows if key in row.consumers)

    def gaps_for(self, consumer: str) -> tuple[CanonicalKnowledgeGap, ...]:
        key = str(consumer or "").strip().casefold()
        return tuple(gap for gap in self.knowledge_gaps if key in gap.consumers)

    def by_status(
        self,
        status: CanonicalMechanicsCoverageStatus,
    ) -> tuple[CanonicalMechanicsCoverageEvidence, ...]:
        return tuple(row for row in self.rows if row.status is status)

    @property
    def decision_critical_gaps(self) -> tuple[CanonicalKnowledgeGap, ...]:
        return tuple(gap for gap in self.knowledge_gaps if gap.blocking)

    @property
    def advisory_gaps(self) -> tuple[CanonicalKnowledgeGap, ...]:
        return tuple(gap for gap in self.knowledge_gaps if not gap.blocking)


class CanonicalMechanicsCoverageAuditService:
    """Turn explicit mechanics-coverage observations into a shared research queue.

    PARTIAL and NICHE coverage remain visible as advisory research.
    MISSING_CRITICAL coverage becomes a blocking knowledge gap because a concrete
    decision cannot be defended without it. This lets the research queue be broad
    without globally disabling Comp Maker, Rotation Maker, or Optimizer for unrelated
    incomplete mechanics.
    """

    def audit(
        self,
        rows: tuple[CanonicalMechanicsCoverageEvidence, ...],
    ) -> CanonicalMechanicsCoverageReport:
        self._validate_unique(rows)
        gaps: list[CanonicalKnowledgeGap] = []
        for row in rows:
            if row.status not in (
                CanonicalMechanicsCoverageStatus.PARTIAL,
                CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
                CanonicalMechanicsCoverageStatus.NICHE,
            ):
                continue
            gaps.append(
                CanonicalKnowledgeGap(
                    domain=row.domain,
                    key=row.key,
                    summary=(
                        f"Canonical mechanics coverage is {row.status.value.replace('_', ' ')}: "
                        f"{row.capability}"
                    ),
                    needed_evidence=(
                        row.missing_evidence
                        or "Retain verified mechanics evidence and expand it when a selected "
                        "build, encounter, or objective depends on this niche capability."
                    ),
                    consumers=row.consumers,
                    source_context=(
                        row.research_context
                        or f"coverage evidence source: {row.evidence_source}"
                    ),
                    blocking=(
                        row.status is CanonicalMechanicsCoverageStatus.MISSING_CRITICAL
                    ),
                )
            )

        return CanonicalMechanicsCoverageReport(
            rows=tuple(rows),
            knowledge_gaps=tuple(gaps),
        )

    @staticmethod
    def _validate_unique(rows: tuple[CanonicalMechanicsCoverageEvidence, ...]) -> None:
        seen: set[str] = set()
        for row in rows:
            key = row.key.casefold()
            if key in seen:
                raise ValueError(f"duplicate canonical mechanics coverage key: {row.key!r}")
            seen.add(key)


__all__ = [
    "CanonicalMechanicsCoverageAuditService",
    "CanonicalMechanicsCoverageEvidence",
    "CanonicalMechanicsCoverageReport",
    "CanonicalMechanicsCoverageStatus",
]
