from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
)
from ui.rotation_canonical_evidence_bundle_support import (
    RotationCanonicalEvidenceBundleSupport,
)


class _GuideService:
    def __init__(self, guide) -> None:
        self.guide = guide

    def get(self, encounter_id):
        assert encounter_id == self.guide.encounter_id
        return self.guide


def _guide() -> EncounterBossGuide:
    return EncounterBossGuide(
        encounter_id="xalvakka",
        content_id="rockgrove",
        content_name="Rockgrove",
        name="Xalvakka",
        summary="",
        location="",
        species="",
        reaction="",
        health_record_present=True,
        health=(("hardmode", "100,000,000"),),
        abilities=(),
        phases=(),
        structural_phases=(),
        timeline_facts=(
            BossGuideTimelineFact(
                fact_id=1,
                canonical_kind="phase",
                fact_type="phase",
                fact_key="phase_2",
                payload={"label": "Phase 2", "starts_at": "70%"},
                review_status="reviewed",
                evidence_count=1,
            ),
        ),
        source_url="https://example.invalid/xalvakka",
        source_page_title="Xalvakka",
        source_revision_id="1",
        retrieved_at="2026-09-11",
        source_license="test",
        content_type="trial",
    )


def _threshold_policy() -> EncounterThresholdRotationDemandPolicy:
    return EncounterThresholdRotationDemandPolicy(
        fact_key="phase_2",
        threshold_fraction=0.70,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        lead_seconds=3.0,
        window_seconds=2.0,
        target_count=12,
        name="Xalvakka Phase 2 healing prep",
    )


def test_bundle_projects_reviewed_threshold_policy_from_explicit_raid_dps() -> None:
    support = RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(_guide()),  # type: ignore[arg-type]
    )

    bundle = support.build(
        encounter_id="xalvakka",
        demand_policies=(),
        threshold_demand_policies=(_threshold_policy(),),
        threshold_damage_segments=(
            RaidDamageSegment(0.0, None, 2_000_000.0, "explicit test raid DPS"),
        ),
        difficulty="hardmode",
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )

    assert bundle.ready is True
    assert bundle.unresolved == ()
    assert len(bundle.demands) == 1
    demand = bundle.demands[0]
    assert demand.name == "Xalvakka Phase 2 healing prep"
    assert demand.start_seconds == 12.0
    assert demand.end_seconds == 17.0
    assert demand.kind is RotationDemandKind.HEALING
    assert demand.pattern is RotationDemandPattern.BURST
    assert demand.target_count == 12


def test_bundle_keeps_missing_threshold_projection_inputs_unresolved() -> None:
    support = RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(_guide()),  # type: ignore[arg-type]
    )

    bundle = support.build(
        encounter_id="xalvakka",
        demand_policies=(),
        threshold_demand_policies=(_threshold_policy(),),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )

    assert bundle.ready is False
    assert bundle.demands == ()
    assert bundle.unresolved == (
        "health-threshold encounter demands require explicit normal, veteran, or hardmode difficulty",
    )
