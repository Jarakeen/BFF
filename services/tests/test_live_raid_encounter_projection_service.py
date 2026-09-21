from __future__ import annotations

from pathlib import Path

from models.raid_plan import RaidPlan, RaidPlanMember
from services.encounter_boss_guide import (
    BossGuidePhase,
    BossGuideTimelineFact,
    EncounterBossGuide,
)
from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjection,
    EncounterGuideStrategyRow,
    EncounterGuideTimelineRow,
)
from services.live_raid_encounter_projection_service import (
    LiveRaidEncounterProjectionService,
)


class FakeGuideService:
    def __init__(self, guide, facts):
        self.guide = guide
        self.facts = facts

    def get(self, encounter_id):
        assert encounter_id == "xalvakka"
        return self.guide

    def reviewed_clock_facts(self, encounter_id):
        assert encounter_id == "xalvakka"
        return self.facts


class FakeEvidenceService:
    def __init__(self, projection):
        self.projection = projection

    def get(self, encounter_id, encounter_name=""):
        assert encounter_id == "xalvakka"
        assert encounter_name == "Xalvakka"
        return self.projection


def _plan() -> RaidPlan:
    return RaidPlan(
        plan_id="rg-pm",
        trial_id="rockgrove",
        name="Performance Mode RG",
        difficulty="Veteran",
        plan_note="Stack tightly for the burn.",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Magrat",
                role="Healer",
                primary_assignment="Major Slayer",
            ),
        ),
    )


def _guide() -> EncounterBossGuide:
    return EncounterBossGuide(
        encounter_id="xalvakka",
        content_id="rockgrove",
        content_name="Rockgrove",
        name="Xalvakka",
        summary="Reviewed encounter summary.",
        location="Xalvakka arena",
        species="",
        reaction="",
        health_record_present=True,
        health=(("veteran", "123"),),
        abilities=(),
        phases=(
            BossGuidePhase(
                phase_id=1,
                label="Main Floor",
                threshold="100% → 70%",
                description="Reviewed phase.",
                source_section="Reviewed canonical timeline",
                source_url="",
                source_revision_id="",
            ),
            BossGuidePhase(
                phase_id=2,
                label="Final Floor",
                threshold="30%",
                description="Reviewed phase.",
                source_section="Reviewed canonical timeline",
                source_url="",
                source_revision_id="",
            ),
        ),
        structural_phases=(),
        timeline_facts=(),
        source_url="",
        source_page_title="",
        source_revision_id="",
        retrieved_at="",
        source_license="",
    )


def test_clock_events_keep_reviewed_point_and_window_timing() -> None:
    facts = (
        BossGuideTimelineFact(
            fact_id=1,
            canonical_kind="phase",
            fact_type="mechanic",
            fact_key="meteor",
            payload={
                "time_seconds": 45,
                "label": "Meteor",
                "description": "Spread for impact.",
            },
            review_status="reviewed",
            evidence_count=2,
        ),
        BossGuideTimelineFact(
            fact_id=2,
            canonical_kind="phase",
            fact_type="damage_window",
            fact_key="burn_window",
            payload={
                "start_seconds": 90,
                "end_seconds": 105,
                "label": "Burn Window",
            },
            review_status="reviewed",
            evidence_count=2,
        ),
    )

    rows = LiveRaidEncounterProjectionService._clock_events(facts)

    assert [row.label for row in rows] == ["Meteor", "Burn Window"]
    assert rows[0].start_seconds == 45
    assert rows[0].end_seconds == 45
    assert rows[0].detail == "Spread for impact."
    assert rows[1].start_seconds == 90
    assert rows[1].end_seconds == 105


def test_context_routes_reviewed_phase_timeline_callouts_and_plan_note() -> None:
    guide = _guide()
    facts = (
        BossGuideTimelineFact(
            fact_id=1,
            canonical_kind="phase",
            fact_type="mechanic",
            fact_key="meteor",
            payload={"at_seconds": 45, "label": "Meteor"},
            review_status="reviewed",
            evidence_count=1,
        ),
    )
    evidence = EncounterGuideEvidenceProjection(
        encounter_id="xalvakka",
        encounter_name="Xalvakka",
        timeline=(
            EncounterGuideTimelineRow(
                marker="70%",
                label="Floor transition",
                detail="Reviewed threshold transition.",
            ),
        ),
        strategy=(
            EncounterGuideStrategyRow(
                mechanic="Soul Tear",
                common_names=(),
                summary="Reviewed mechanic.",
                mitigation="Block the hit.",
            ),
        ),
        callouts=("Soul Tear: Block the hit.",),
        brief=(),
        role_impact=(),
        evidence_rows=3,
    )

    service = object.__new__(LiveRaidEncounterProjectionService)
    service.guide_service = FakeGuideService(guide, facts)
    service.evidence_service = FakeEvidenceService(evidence)

    context = service.context_for(_plan(), "xalvakka")

    assert context is not None
    assert context.encounter_name == "Xalvakka"
    assert context.content_name == "Rockgrove"
    assert context.phase_lines == (
        "100% → 70% • Main Floor",
        "30% • Final Floor",
    )
    assert context.condition_events[0].marker == "70%"
    assert context.condition_events[0].label == "Floor transition"
    assert context.callouts == ("Soul Tear: Block the hit.",)
    assert context.checklist == (
        "Soul Tear: Block the hit.",
        "Plan note: Stack tightly for the burn.",
    )
    assert context.clock_events[0].label == "Meteor"
    assert context.clock_events[0].start_seconds == 45


def test_unreviewed_or_malformed_clock_payloads_do_not_become_live_events() -> None:
    facts = (
        BossGuideTimelineFact(
            fact_id=1,
            canonical_kind="phase",
            fact_type="mechanic",
            fact_key="threshold_only",
            payload={"threshold": "70%", "label": "Threshold"},
            review_status="reviewed",
            evidence_count=2,
        ),
        BossGuideTimelineFact(
            fact_id=2,
            canonical_kind="phase",
            fact_type="mechanic",
            fact_key="bad_window",
            payload={"start_seconds": 60, "end_seconds": 45, "label": "Bad Window"},
            review_status="reviewed",
            evidence_count=2,
        ),
    )

    assert LiveRaidEncounterProjectionService._clock_events(facts) == ()
