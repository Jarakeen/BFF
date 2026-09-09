from __future__ import annotations

from collections.abc import Iterable

from minmax.character_build.passive_grant import PassiveGrant
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandWindow
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
from services.rotation_candidate_generation_service import RotationRefreshLeadCandidateOption
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_recovery_heavy_candidate_generation_bridge_service import (
    RecoveryCandidateEvaluatorResolver,
    RecoveryPressureWaitDecisionFactory,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalScorecardResolver,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    VerifiedRecoveryHeavyRestorationResolver,
)
from services.rotation_support_cadence_progression_runner_service import (
    RotationSupportCadenceProgressionRun,
)
from ui.components.rotation_cadence_progression_card import (
    RotationCadenceProgressionCard,
)
from ui.rotation_canonical_candidate_render_support import (
    RotationCanonicalCandidateRenderEvidence,
    RotationCanonicalCandidateRenderSupport,
)
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateResult,
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_dashboard_page import RotationDashboardPage
from ui.rotation_generation_support import RotationGenerationRequest
from ui.rotation_pdf_export_support import install_rotation_pdf_export
from ui.rotation_support_cadence_progression_render_support import (
    RotationSupportCadenceProgressionRenderEvidence,
    RotationSupportCadenceProgressionRenderSupport,
)
from ui.rotation_timeline_dashboard_support import install_rotation_timeline


class CanonicalRotationDashboardPage(RotationDashboardPage):
    """Rotation dashboard with explicit canonical-candidate execution seams."""

    def __init__(
        self,
        parent=None,
        *,
        canonical_candidates: RotationDashboardCanonicalCandidateSupport | None = None,
        canonical_render: RotationCanonicalCandidateRenderSupport | None = None,
        cadence_progression_render: RotationSupportCadenceProgressionRenderSupport | None = None,
    ) -> None:
        super().__init__(parent)
        install_rotation_timeline(self)
        install_rotation_pdf_export(self)
        self.cadence_progression_card = RotationCadenceProgressionCard()
        self.workspace_layout.addWidget(self.cadence_progression_card)
        self.rotation_canonical_candidates = (
            canonical_candidates
            or RotationDashboardCanonicalCandidateSupport(
                generation=self.rotation_generation,
            )
        )
        self.rotation_canonical_render = (
            canonical_render or RotationCanonicalCandidateRenderSupport()
        )
        self.rotation_cadence_progression_render = (
            cadence_progression_render or RotationSupportCadenceProgressionRenderSupport()
        )
        self.last_canonical_candidate_result: (
            RotationDashboardCanonicalCandidateResult | None
        ) = None
        self.last_canonical_render_evidence: (
            RotationCanonicalCandidateRenderEvidence | None
        ) = None
        self.last_cadence_progression_run: RotationSupportCadenceProgressionRun | None = None
        self.last_cadence_progression_render_evidence: (
            RotationSupportCadenceProgressionRenderEvidence | None
        ) = None

    def canonical_generation_request(self) -> RotationGenerationRequest:
        """Capture the dashboard's current saved-build generation inputs exactly once."""
        build = self._selected_build()
        if build is None:
            raise ValueError("select a saved build before canonical candidate evaluation")

        priorities = self.ability_priorities()
        if not priorities:
            raise ValueError(
                "canonical candidate evaluation requires explicit dashboard ability priorities"
            )

        settings = self.rotation_settings()
        return RotationGenerationRequest(
            duration_seconds=60.0,
            rotation_type=str(settings["rotation_type"]),
            potion=str(settings["potion"]),
            potion_on_cooldown=bool(settings["potion_on_cooldown"]),
            weave_light_attacks=True,
            ultimate_bar=str(settings["ultimate_bar"]),
            starting_ultimate=float(settings["starting_ultimate"]),
            use_scheduled_combat_attacks_for_ultimate=bool(
                settings["use_scheduled_combat_attacks_for_ultimate"]
            ),
            ability_priorities=priorities,
        )

    def evaluate_canonical_candidates(
        self,
        *,
        evaluator_resolver: RecoveryCandidateEvaluatorResolver,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        demands: Iterable[RotationDemandWindow] = (),
        options: Iterable[RotationRefreshLeadCandidateOption] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        requirements: Iterable[RotationEffectUptimeRequirement] = (),
        passives: Iterable[PassiveGrant] = (),
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        baseline_id: str = "baseline",
        character_id: str | None = None,
        coverage_report: CanonicalMechanicsCoverageReport | None = None,
    ) -> RotationDashboardCanonicalCandidateResult:
        """Run the page's current saved build through the canonical candidate path."""
        build = self._selected_build()
        if build is None:
            raise ValueError("select a saved build before canonical candidate evaluation")

        request = self.canonical_generation_request()
        result = self.rotation_canonical_candidates.run_effects(
            player_build=build,
            generation_request=request,
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            demands=tuple(demands),
            options=tuple(options),
            wait_decision_factory=wait_decision_factory,
            requirements=tuple(requirements),
            passives=tuple(passives),
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            baseline_id=baseline_id,
            character_id=character_id,
            coverage_report=coverage_report,
        )
        self.last_canonical_candidate_result = result
        self.last_canonical_render_evidence = None
        self.last_cadence_progression_run = None
        self.last_cadence_progression_render_evidence = None
        self.cadence_progression_card.clear_report()
        return result

    def evaluate_canonical_evidence_bundle(
        self,
        bundle: RotationCanonicalEvidenceBundle,
        *,
        character_id: str | None = None,
    ) -> RotationDashboardCanonicalCandidateResult:
        """Evaluate one already-assembled canonical encounter/build evidence bundle."""
        if not bundle.ready:
            details = [
                str(item).strip()
                for item in getattr(bundle, "unresolved", ())
                if str(item).strip()
            ]
            blocking_gaps = getattr(bundle, "blocking_knowledge_gaps", None)
            if blocking_gaps is None:
                blocking_gaps = tuple(
                    gap
                    for gap in getattr(bundle, "knowledge_gaps", ())
                    if bool(getattr(gap, "blocking", True))
                )
            for gap in blocking_gaps:
                summary = str(getattr(gap, "summary", "") or "").strip()
                needed = str(getattr(gap, "needed_evidence", "") or "").strip()
                if summary and needed:
                    details.append(f"{summary} Bring back: {needed}")
                elif summary:
                    details.append(summary)
            detail = "; ".join(details) or "unspecified unresolved evidence"
            raise ValueError(
                "canonical rotation evidence bundle is not ready for candidate evaluation: "
                + detail
            )

        return self.evaluate_canonical_candidates(
            evaluator_resolver=bundle.evaluator_resolver,
            scorecard_resolver=bundle.scorecard_resolver,
            resource=bundle.resource,
            maximum_amount=bundle.maximum_amount,
            trigger_fraction=bundle.trigger_fraction,
            restoration_resolver=bundle.restoration_resolver,
            demands=bundle.demands,
            options=bundle.options,
            wait_decision_factory=bundle.wait_decision_factory,
            requirements=bundle.requirements,
            passives=bundle.passives,
            reserve_assessment_resolver=bundle.reserve_assessment_resolver,
            max_iterations=bundle.max_iterations,
            baseline_id=bundle.baseline_id,
            character_id=character_id,
            coverage_report=getattr(bundle, "coverage_report", None),
        )

    def apply_canonical_candidate_result(
        self,
        result: RotationDashboardCanonicalCandidateResult | None = None,
    ) -> RotationCanonicalCandidateRenderEvidence | None:
        """Render only evidence belonging to the selected final stabilized plan."""
        resolved = result or self.last_canonical_candidate_result
        if resolved is None:
            raise ValueError("no canonical candidate evaluation is available to render")

        evidence = self.rotation_canonical_render.build(resolved.candidate_result)
        self.last_canonical_render_evidence = evidence
        if evidence is None:
            self.status.warning(
                "Canonical candidate evaluation produced no selectable rotation; "
                "the existing dashboard plan was not replaced."
            )
            return None

        self.set_rotation_plan(evidence.plan)
        self.duration_evidence_card.set_evidence(evidence.duration_evidence)
        self.set_sustain_projection(evidence.sustain_projection)
        return evidence

    def apply_cadence_progression_run(
        self,
        run: RotationSupportCadenceProgressionRun,
    ) -> RotationSupportCadenceProgressionRenderEvidence:
        """Render one completed cadence progression run as one consistent final bundle."""
        evidence = self.rotation_cadence_progression_render.build(run)
        self.last_cadence_progression_run = run
        self.last_cadence_progression_render_evidence = evidence

        self.set_rotation_plan(evidence.plan)
        self.duration_evidence_card.set_evidence(evidence.duration_evidence)
        self.set_sustain_projection(evidence.sustain_projection)

        report = evidence.report
        self.cadence_progression_card.set_report(report)
        self.status.info(
            "Cadence optimization: "
            f"{report.advanced_steps} accepted improvement(s) across "
            f"{report.iterations} iteration(s). {report.stop_summary}"
        )
        return evidence


__all__ = ["CanonicalRotationDashboardPage"]
