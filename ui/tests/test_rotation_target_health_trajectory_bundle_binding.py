from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
)
from ui.rotation_canonical_evidence_bundle_support import (
    RotationCanonicalEvidenceBundleSupport,
)
from ui.rotation_generate_dd_target_health_role_evidence_support import (
    RotationGenerateDDTargetHealthRoleEvidenceSupport,
)


class _GuideService:
    def __init__(self, guide) -> None:
        self.guide = guide

    def get(self, encounter_id):
        assert encounter_id == self.guide.encounter_id
        return self.guide


class _EmptyTargetHealthRegistry:
    def load(self):
        return ()


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
        retrieved_at="2026-09-13",
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
        name="Phase 2 prep",
    )


def test_bundle_trajectory_binds_live_dd_target_health_snapshots() -> None:
    bundle = RotationCanonicalEvidenceBundleSupport(
        guide_service=_GuideService(_guide()),  # type: ignore[arg-type]
    ).build(
        encounter_id="xalvakka",
        demand_policies=(),
        threshold_demand_policies=(_threshold_policy(),),
        threshold_damage_segments=(
            RaidDamageSegment(0.0, None, 2_000_000.0, "explicit raid DPS"),
        ),
        difficulty="hardmode",
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )

    assert bundle.target_health_trajectory is not None
    assert bundle.target_health_trajectory.maximum_health == pytest.approx(100_000_000.0)

    support = RotationGenerateDDTargetHealthRoleEvidenceSupport(
        database_path="unused-test.db",
        periodic_target_health_semantics_registry=_EmptyTargetHealthRegistry(),  # type: ignore[arg-type]
    )
    plan_evidence = support._build_plan_evidence_provider(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=bundle,
        static_context=SimpleNamespace(),
        target_resistance=18200.0,
        periodic_runtime_semantics=(),
        runtime_build_context_resolver=None,
        runtime_target_combat_state_resolver=None,
        runtime_target_resistance_resolver=None,
        activation_anchor_resolver=None,
    )

    router = plan_evidence.role_output_evidence_provider.action_damage_evidence_provider
    skill_provider = router._providers[RotationActionKind.SKILL]

    assert skill_provider.target_identity == "xalvakka"
    assert skill_provider.runtime_target_snapshot_resolver is not None

    start = skill_provider.runtime_target_snapshot_resolver(0.0)
    ten_seconds = skill_provider.runtime_target_snapshot_resolver(10.0)
    threshold = skill_provider.runtime_target_snapshot_resolver(15.0)

    assert start is not None
    assert ten_seconds is not None
    assert threshold is not None
    assert start.target("xalvakka").health_fraction() == pytest.approx(1.0)  # type: ignore[union-attr]
    assert ten_seconds.target("xalvakka").health_fraction() == pytest.approx(0.8)  # type: ignore[union-attr]
    assert threshold.target("xalvakka").health_fraction() == pytest.approx(0.7)  # type: ignore[union-attr]
