from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationPlan
from services.rotation_support_cadence_progression_report_service import (
    RotationSupportCadenceProgressionReport,
    RotationSupportCadenceProgressionReportService,
)
from services.rotation_support_cadence_progression_runner_service import (
    RotationSupportCadenceProgressionRun,
)
from services.rotation_sustain_service import RotationSustainProjection
from ui.rotation_duration_evidence_support import (
    RotationDurationEvidence,
    RotationDurationEvidenceSupport,
)


@dataclass(frozen=True)
class RotationSupportCadenceProgressionRenderEvidence:
    """Final accepted cadence progression state safe for dashboard rendering."""

    plan: RotationPlan
    sustain_projection: RotationSustainProjection
    duration_evidence: RotationDurationEvidence
    report: RotationSupportCadenceProgressionReport


class RotationSupportCadenceProgressionRenderSupport:
    """Join one completed progression run to evidence for its exact final plan.

    This adapter does not optimize, rank, or reinterpret mechanics. It takes the
    runner's final accepted plan/sustain pair, builds ordinary duration-card evidence
    for that same plan, and attaches the already-read-only progression report.
    """

    def __init__(
        self,
        *,
        duration_evidence: RotationDurationEvidenceSupport | None = None,
        report_service: RotationSupportCadenceProgressionReportService | None = None,
    ) -> None:
        self.duration_evidence = duration_evidence or RotationDurationEvidenceSupport()
        self.report_service = report_service or RotationSupportCadenceProgressionReportService()

    def build(
        self,
        run: RotationSupportCadenceProgressionRun,
    ) -> RotationSupportCadenceProgressionRenderEvidence:
        report = self.report_service.build(run)
        return RotationSupportCadenceProgressionRenderEvidence(
            plan=run.final_plan,
            sustain_projection=run.final_sustain,
            duration_evidence=self.duration_evidence.build(run.final_plan),
            report=report,
        )


__all__ = [
    "RotationSupportCadenceProgressionRenderEvidence",
    "RotationSupportCadenceProgressionRenderSupport",
]
