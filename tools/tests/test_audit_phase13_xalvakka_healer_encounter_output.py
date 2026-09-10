from types import SimpleNamespace

import pytest

from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.encounter_boss_guide import BossGuidePhase, EncounterBossGuide
from tools.audit_phase13_xalvakka_healer_encounter_output import (
    _SourceStructuralThresholdProjectionService,
    _candidate,
    _guide_from_source_definition,
    _load_reviewed_runtime_observations,
    _window_actions,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=9.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Before",
                bar="front",
            ),
            RotationAction(
                time_seconds=10.0,
                sequence=1,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=10.0,
                sequence=2,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                time_seconds=11.5,
                sequence=3,
                kind=RotationActionKind.SKILL,
                name="Energy Orb",
                bar="back",
            ),
            RotationAction(
                time_seconds=12.0,
                sequence=4,
                kind=RotationActionKind.SKILL,
                name="Boundary",
                bar="front",
            ),
        ),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Xalvakka Phase 2 healing prep",
        start_seconds=10.0,
        end_seconds=12.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def _source_guide() -> EncounterBossGuide:
    phase = BossGuidePhase(
        phase_id=1,
        label="Phase 2",
        threshold="70%",
        description="source phase",
        source_section="source-backed structural phase",
        source_url="https://example.test/xalvakka",
        source_revision_id="r1",
    )
    return EncounterBossGuide(
        encounter_id="xalvakka",
        content_id="rockgrove",
        content_name="Rockgrove",
        name="Xalvakka",
        summary="",
        location="",
        species="Harvester",
        reaction="",
        health_record_present=True,
        health=(("hardmode", "214,233,024 (Hard Mode)"),),
        abilities=(),
        phases=(phase,),
        structural_phases=(phase,),
        timeline_facts=(),
        source_url="https://example.test/xalvakka",
        source_page_title="Xalvakka",
        source_revision_id="r1",
        retrieved_at="",
        source_license="",
    )


def test_candidate_wraps_exact_plan_without_rescheduling():
    plan = _plan()
    candidate = _candidate("xalvakka-aware", plan)

    assert candidate.candidate_id == "xalvakka-aware"
    assert candidate.plan is plan
    assert candidate.refresh_leads == ()
    assert candidate.action_claims == ()


def test_window_trace_excludes_light_attacks_and_end_boundary():
    actions = _window_actions(_plan(), _demand())

    assert [(action.time_seconds, action.name, action.bar) for action in actions] == [
        (10.0, "Combat Prayer", "front"),
        (11.5, "Energy Orb", "back"),
    ]


def test_missing_runtime_fixture_means_no_observations_are_invented():
    observations, unresolved = _load_reviewed_runtime_observations(
        database_path=None,
        fixture_path=None,
    )

    assert observations == ()
    assert unresolved == ()


def test_source_structural_threshold_fallback_projects_exact_phase_threshold():
    result = _SourceStructuralThresholdProjectionService().project(
        guide=_source_guide(),
        difficulty="hardmode",
        damage_segments=(
            RaidDamageSegment(
                0.0,
                None,
                2_000_000.0,
                "test raid DPS assumption",
            ),
        ),
    )

    assert result.maximum_health == 214_233_024
    assert result.unresolved == ()
    assert len(result.points) == 1
    point = result.points[0]
    assert point.fact_key == "phase_2"
    assert point.threshold_fraction == pytest.approx(0.70)
    assert point.time_seconds == pytest.approx((214_233_024 * 0.30) / 2_000_000.0)
    assert "source-backed structural phase threshold" in point.reason


def test_source_definition_adapter_does_not_claim_reviewed_timeline_facts():
    definition = SimpleNamespace(
        encounter_id="xalvakka",
        content_id="rockgrove",
        name="Xalvakka",
        difficulty_health=(("hardmode", "214,233,024 (Hard Mode)"),),
        source=SimpleNamespace(
            url="https://example.test/xalvakka",
            page_title="Xalvakka",
            revision_id="r1",
            retrieved_at="2026-09-10",
            license="CC BY-SA",
        ),
        actors=(SimpleNamespace(species="Harvester"),),
        phases=(
            SimpleNamespace(
                label="Phase 2",
                threshold="70%",
                description="literal source phase",
            ),
        ),
    )

    guide = _guide_from_source_definition(definition)

    assert guide.encounter_id == "xalvakka"
    assert guide.timeline_facts == ()
    assert guide.structural_phases[0].threshold == "70%"
    assert guide.structural_phases[0].source_section == "source-backed structural phase"
