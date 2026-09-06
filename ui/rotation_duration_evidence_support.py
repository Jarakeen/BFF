from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationPlan
from services.rotation_duration_analysis_service import (
    RotationDurationAnalysisService,
    RotationDurationProjection,
)


@dataclass(frozen=True)
class RotationDurationEvidenceRow:
    ability: str
    bar: str
    duration_seconds: float
    casts: int
    uptime_percent: float
    gap_seconds: float
    premature_seconds: float


@dataclass(frozen=True)
class RotationDurationEvidence:
    rows: tuple[RotationDurationEvidenceRow, ...]
    summary: str
    detail: str
    unresolved: tuple[str, ...]


class RotationDurationEvidenceSupport:
    """Convert authoritative duration analysis into dashboard-ready evidence.

    This layer formats evidence only. It does not infer durations, modify the
    rotation, or reinterpret the recast analyzer's results.
    """

    def __init__(
        self,
        analysis_service: RotationDurationAnalysisService | None = None,
    ) -> None:
        self.analysis_service = analysis_service or RotationDurationAnalysisService()

    def build(self, plan: RotationPlan) -> RotationDurationEvidence:
        projection = self.analysis_service.analyze(plan)
        return self.from_projection(projection)

    @staticmethod
    def from_projection(
        projection: RotationDurationProjection,
    ) -> RotationDurationEvidence:
        rows = tuple(
            RotationDurationEvidenceRow(
                ability=summary.skill_name,
                bar=(summary.bar or "any").title(),
                duration_seconds=float(summary.duration_seconds),
                casts=int(summary.cast_count),
                uptime_percent=float(summary.uptime_fraction) * 100.0,
                gap_seconds=float(summary.total_gap_seconds),
                premature_seconds=float(summary.total_premature_seconds),
            )
            for summary in projection.analysis.summaries
        )

        if rows:
            average_uptime = sum(row.uptime_percent for row in rows) / len(rows)
            gap_total = sum(row.gap_seconds for row in rows)
            premature_total = sum(row.premature_seconds for row in rows)
            summary = (
                f"Verified duration rules: {len(rows)} • "
                f"Average projected uptime: {average_uptime:.1f}%"
            )
            detail = (
                f"Total uncovered gap: {gap_total:.1f}s • "
                f"Premature overlap: {premature_total:.1f}s • "
                f"Unresolved duration evidence: {len(projection.unresolved)}"
            )
        else:
            summary = "Verified duration rules: none available for the generated plan"
            detail = (
                "Recast timing remains unresolved until canonical positive skill durations "
                "are available."
            )

        return RotationDurationEvidence(
            rows=rows,
            summary=summary,
            detail=detail,
            unresolved=tuple(projection.unresolved),
        )
