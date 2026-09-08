from __future__ import annotations

import pytest

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
from ui.rotation_canonical_evidence_bundle_support import (
    RotationCanonicalEvidenceBundleSupport,
)


def _guide(*, reviewed: bool = True) -> EncounterBossGuide:
    fact = BossGuideTimelineFact(
        fact_id=7,
        canonical_kind="phase",
        fact_type="clock_window",
        fact_key="required_support_window",
        payload={"label": "Required Support", "time_seconds": 10.0},
        review_status="reviewed" if reviewed else "draft",
        evidence_count=2,
    )
    return EncounterBossGuide(
        encounter_id="test-encounter",
        content_id="test-content",
        content_name="Test Trial",
        name="Test Boss",
        summary="",
        location="",
        species="",
        reaction="",
        health_record_present=False,
        health=(),
        abilities=(),
        phases=(),
        structural_phases=(),
        timeline_facts=(fact,),
        source_url="",
        source_page_title="",
        source_revision_id="",
        retrieved_at="",
        source_license="",
    )


class _GuideService:
    def __init__(self, guide: EncounterBossGuide) -> None:
        self.guide = guide
        self.calls: list[str] = []

    def get(self, encounter_id: str) -> EncounterBossGuide:
        self.calls.append(encounter_id)
        return self.guide


def _policy() -> EncounterRotationDemandPolicy:
    return EncounterRotationDemandPolicy(
        fact_key="required_support_window",
        kind=RotationDemandKind.SUPPORT,
        pattern=RotationDemandPattern.BURST,
        lead_seconds=2.0,
        point_window_seconds=3.0,
    )


def _coverage_report(*, status: CanonicalMechanicsCoverageStatus):
    missing = None
    if status in (
        CanonicalMechanicsCoverageStatus.PARTIAL,
        CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
    ):
        missing = "bring back exact runtime mechanics evidence"
    row = CanonicalMechanicsCoverageEvidence(
        domain=CanonicalKnowledgeDomain.SKILL_MECHANIC,
        key=f"rotation-test:{status.value}",
        status=status,
        capability="test rotation runtime capability",
        evidence_source="test fixture",
        consumers=("rotation_maker",),
        missing_evidence=missing,
    )
    return CanonicalMechanicsCoverageAuditService().audit((row,))


def _coverage_row(
    *,
    key: str,
    status: CanonicalMechanicsCoverageStatus,
) -> CanonicalMechanicsCoverageEvidence:
    missing = None
    if status in (
        CanonicalMechanicsCoverageStatus.PARTIAL,
        CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
    ):
        missing = f"bring back exact runtime mechanics evidence for {key}"
    return CanonicalMechanicsCoverageEvidence(
        domain=CanonicalKnowledgeDomain.SKILL_MECHANIC,
        key=key,
        status=status,
        capability=f"rotation capability for {key}",
        evidence_source="test fixture",
        consumers=("rotation_maker",),
        missing_evidence=missing,
    )


def _support() -> RotationCanonicalEvidenceBundleSupport:
    return RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(_guide()),
        demand_service=EncounterRotationDemandService(),
    )


def _build_with_coverage(status: CanonicalMechanicsCoverageStatus):
    key = f"rotation-test:{status.value}"
    report = _coverage_report(status=status)
    return _support().build(
        encounter_id="test-encounter",
        demand_policies=(_policy(),),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        coverage_report=report,
        coverage_dependency_keys=(key,),
    )


def _coverage_build_kwargs() -> dict:
    return dict(
        encounter_id="test-encounter",
        demand_policies=(_policy(),),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )


def test_bundle_projects_reviewed_encounter_demands_and_preserves_explicit_policy() -> None:
    guide_service = _GuideService(_guide())
    support = RotationCanonicalEvidenceBundleSupport(
        guide_service=guide_service,
        demand_service=EncounterRotationDemandService(),
    )
    evaluator = object()
    scorecard = object()
    restoration = object()
    wait_factory = object()
    reserve = object()

    bundle = support.build(
        encounter_id="test-encounter",
        demand_policies=(_policy(),),
        evaluator_resolver=evaluator,
        scorecard_resolver=scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=restoration,
        options=("option-a",),
        requirements=("effect-a",),
        passives=("passive-a", "passive-b"),
        wait_decision_factory=wait_factory,
        reserve_assessment_resolver=reserve,
        max_iterations=8,
        baseline_id="dashboard-baseline",
    )

    assert guide_service.calls == ["test-encounter"]
    assert bundle.encounter_id == "test-encounter"
    assert bundle.encounter_name == "Test Boss"
    assert bundle.ready is True
    assert bundle.unresolved == ()
    assert len(bundle.demands) == 1
    demand = bundle.demands[0]
    assert demand.name == "Required Support"
    assert demand.start_seconds == 8.0
    assert demand.end_seconds == 13.0
    assert demand.kind is RotationDemandKind.SUPPORT
    assert demand.pattern is RotationDemandPattern.BURST
    assert bundle.evaluator_resolver is evaluator
    assert bundle.scorecard_resolver is scorecard
    assert bundle.resource is ResourceType.MAGICKA
    assert bundle.maximum_amount == 32000
    assert bundle.trigger_fraction == 0.35
    assert bundle.restoration_resolver is restoration
    assert bundle.options == ("option-a",)
    assert bundle.requirements == ("effect-a",)
    assert bundle.passives == ("passive-a", "passive-b")
    assert bundle.wait_decision_factory is wait_factory
    assert bundle.reserve_assessment_resolver is reserve
    assert bundle.max_iterations == 8
    assert bundle.baseline_id == "dashboard-baseline"
    assert bundle.coverage_report is None


def test_bundle_fails_readiness_when_requested_encounter_fact_is_not_reviewed() -> None:
    support = RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(_guide(reviewed=False)),
        demand_service=EncounterRotationDemandService(),
    )

    bundle = support.build(
        encounter_id="test-encounter",
        demand_policies=(_policy(),),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )

    assert bundle.ready is False
    assert bundle.demands == ()
    assert len(bundle.unresolved) == 1
    assert "not reviewed" in bundle.unresolved[0]


def test_bundle_rejects_invalid_recovery_policy_instead_of_inventing_defaults() -> None:
    support = RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(_guide()),
        demand_service=EncounterRotationDemandService(),
    )
    common = dict(
        encounter_id="test-encounter",
        demand_policies=(_policy(),),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        restoration_resolver=object(),
    )

    with pytest.raises(ValueError, match="positive maximum_amount"):
        support.build(maximum_amount=0, trigger_fraction=0.35, **common)
    with pytest.raises(ValueError, match="between 0 and 1"):
        support.build(maximum_amount=32000, trigger_fraction=1.2, **common)
    with pytest.raises(ValueError, match="max_iterations must be positive"):
        support.build(
            maximum_amount=32000,
            trigger_fraction=0.35,
            max_iterations=0,
            **common,
        )


def test_bundle_ingests_partial_coverage_as_visible_advisory_research() -> None:
    bundle = _build_with_coverage(CanonicalMechanicsCoverageStatus.PARTIAL)

    assert bundle.ready is True
    assert bundle.blocking_knowledge_gaps == ()
    assert [gap.key for gap in bundle.advisory_knowledge_gaps] == ["rotation-test:partial"]
    assert bundle.research_for("rotation_maker") == bundle.advisory_knowledge_gaps


def test_bundle_ingests_niche_coverage_without_blocking_rotation_readiness() -> None:
    bundle = _build_with_coverage(CanonicalMechanicsCoverageStatus.NICHE)

    assert bundle.ready is True
    assert bundle.blocking_knowledge_gaps == ()
    assert [gap.key for gap in bundle.advisory_knowledge_gaps] == ["rotation-test:niche"]


def test_bundle_ingests_missing_critical_coverage_as_readiness_blocker() -> None:
    bundle = _build_with_coverage(CanonicalMechanicsCoverageStatus.MISSING_CRITICAL)

    assert bundle.ready is False
    assert [gap.key for gap in bundle.blocking_knowledge_gaps] == [
        "rotation-test:missing_critical"
    ]
    assert bundle.advisory_knowledge_gaps == ()


def test_bundle_retains_broad_coverage_for_later_build_dependency_discovery() -> None:
    report = _coverage_report(status=CanonicalMechanicsCoverageStatus.MISSING_CRITICAL)

    bundle = _support().build(
        **_coverage_build_kwargs(),
        coverage_report=report,
    )

    assert bundle.coverage_report is report
    assert bundle.knowledge_gaps == ()
    assert bundle.ready is True


def test_bundle_declared_dependencies_ignore_unrelated_critical_coverage() -> None:
    report = CanonicalMechanicsCoverageAuditService().audit(
        (
            _coverage_row(
                key="selected-ready",
                status=CanonicalMechanicsCoverageStatus.CALCULATION_READY,
            ),
            _coverage_row(
                key="selected-partial",
                status=CanonicalMechanicsCoverageStatus.PARTIAL,
            ),
            _coverage_row(
                key="unrelated-critical",
                status=CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
            ),
        )
    )

    bundle = _support().build(
        **_coverage_build_kwargs(),
        coverage_report=report,
        coverage_dependency_keys=("selected-ready", "selected-partial"),
    )

    assert bundle.ready is True
    assert bundle.coverage_report is report
    assert bundle.blocking_knowledge_gaps == ()
    assert [gap.key for gap in bundle.advisory_knowledge_gaps] == ["selected-partial"]


def test_bundle_declared_missing_dependency_blocks_readiness() -> None:
    report = CanonicalMechanicsCoverageAuditService().audit(
        (
            _coverage_row(
                key="known-ready",
                status=CanonicalMechanicsCoverageStatus.CALCULATION_READY,
            ),
        )
    )

    bundle = _support().build(
        **_coverage_build_kwargs(),
        coverage_report=report,
        coverage_dependency_keys=("known-ready", "build-specific:unknown-mechanic"),
    )

    assert bundle.ready is False
    assert [gap.key for gap in bundle.blocking_knowledge_gaps] == [
        "build-specific:unknown-mechanic"
    ]
    assert "no canonical coverage evidence" in bundle.blocking_knowledge_gaps[0].summary
