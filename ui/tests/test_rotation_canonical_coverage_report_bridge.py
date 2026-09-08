from __future__ import annotations

from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.canonical_knowledge_gap import CanonicalKnowledgeDomain
from services.canonical_mechanics_coverage_audit import (
    CanonicalMechanicsCoverageAuditService,
    CanonicalMechanicsCoverageEvidence,
    CanonicalMechanicsCoverageStatus,
)
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide
from services.encounter_rotation_demand_service import (
    EncounterRotationDemandPolicy,
    EncounterRotationDemandService,
)
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundleSupport


class _GuideService:
    def get(self, encounter_id: str) -> EncounterBossGuide:
        return EncounterBossGuide(
            encounter_id=encounter_id,
            content_id="trial",
            content_name="Trial",
            name="Boss",
            summary="",
            location="",
            species="",
            reaction="",
            health_record_present=False,
            health=(),
            abilities=(),
            phases=(),
            structural_phases=(),
            timeline_facts=(
                BossGuideTimelineFact(
                    fact_id=1,
                    canonical_kind="phase",
                    fact_type="clock_window",
                    fact_key="window",
                    payload={"label": "Window", "time_seconds": 10.0},
                    review_status="reviewed",
                    evidence_count=1,
                ),
            ),
            source_url="",
            source_page_title="",
            source_revision_id="",
            retrieved_at="",
            source_license="",
        )


def _policy() -> EncounterRotationDemandPolicy:
    return EncounterRotationDemandPolicy(
        fact_key="window",
        kind=RotationDemandKind.SUPPORT,
        pattern=RotationDemandPattern.BURST,
        lead_seconds=0.0,
        point_window_seconds=1.0,
    )


def _coverage(status: CanonicalMechanicsCoverageStatus):
    return CanonicalMechanicsCoverageAuditService().audit(
        (
            CanonicalMechanicsCoverageEvidence(
                domain=CanonicalKnowledgeDomain.PASSIVE,
                key="warden:passive-duration",
                status=status,
                capability="Warden passive duration semantics are not fully catalogued.",
                evidence_source="verified audit fixture",
                consumers=("comp_maker", "rotation_maker", "optimizer"),
                missing_evidence=(
                    "Provide exact rank, prerequisites, affected effects, magnitude, stacking, "
                    "bar/slot/equipment requirements and provenance."
                ),
            ),
        )
    )


def _build(report):
    return RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(),
        demand_service=EncounterRotationDemandService(),
    ).build(
        encounter_id="boss",
        demand_policies=(_policy(),),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        coverage_report=report,
    )


def test_partial_coverage_report_becomes_visible_advisory_research() -> None:
    bundle = _build(_coverage(CanonicalMechanicsCoverageStatus.PARTIAL))

    assert bundle.ready is True
    assert bundle.blocking_knowledge_gaps == ()
    assert len(bundle.advisory_knowledge_gaps) == 1
    assert bundle.research_for("rotation_maker") == bundle.advisory_knowledge_gaps
    assert bundle.research_for("optimizer") == bundle.advisory_knowledge_gaps


def test_missing_critical_coverage_report_blocks_canonical_rotation_readiness() -> None:
    bundle = _build(_coverage(CanonicalMechanicsCoverageStatus.MISSING_CRITICAL))

    assert bundle.ready is False
    assert len(bundle.blocking_knowledge_gaps) == 1
    assert bundle.advisory_knowledge_gaps == ()
    assert "passive" in bundle.blocking_knowledge_gaps[0].domain.value


def test_coverage_report_only_merges_rotation_relevant_gaps() -> None:
    report = CanonicalMechanicsCoverageAuditService().audit(
        (
            CanonicalMechanicsCoverageEvidence(
                domain=CanonicalKnowledgeDomain.OTHER,
                key="comp-only",
                status=CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
                capability="Comp-only evidence is missing.",
                evidence_source="fixture",
                consumers=("comp_maker",),
                missing_evidence="Provide comp-only evidence.",
            ),
        )
    )

    bundle = _build(report)

    assert bundle.ready is True
    assert bundle.knowledge_gaps == ()
