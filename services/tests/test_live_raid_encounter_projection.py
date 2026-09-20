from pathlib import Path

from services.encounter_boss_guide import BossGuideEncounterSummary, BossGuideTimelineFact
from services.live_raid_encounter_projection_service import LiveRaidEncounterProjectionService
from services.raid_section_state_service import RaidSectionStateService


class _GuideIndex:
    def encounter_summaries(self):
        return (
            BossGuideEncounterSummary(
                encounter_id="nahviintaas",
                content_id="sunspire",
                content_name="Sunspire",
                name="Nahviintaas",
                location="",
            ),
            BossGuideEncounterSummary(
                encounter_id="xalvakka",
                content_id="rockgrove",
                content_name="Rockgrove",
                name="Xalvakka",
                location="",
            ),
        )


def test_live_raid_trial_filter_only_returns_encounters_for_selected_trial(tmp_path):
    service = object.__new__(LiveRaidEncounterProjectionService)
    service.guide_service = _GuideIndex()

    rows = service.encounters_for_trial("Sunspire")

    assert [row.encounter_id for row in rows] == ["nahviintaas"]


def test_live_raid_clock_events_require_explicit_clock_fields():
    timed = BossGuideTimelineFact(
        fact_id=1,
        canonical_kind="mechanic",
        fact_type="mechanic",
        fact_key="portal",
        payload={
            "time_seconds": 15,
            "label": "Portal team ready",
            "description": "Both teams confirm position.",
        },
        review_status="reviewed",
        evidence_count=2,
    )
    threshold_only = BossGuideTimelineFact(
        fact_id=2,
        canonical_kind="phase_transition",
        fact_type="phase_transition",
        fact_key="execute",
        payload={
            "threshold": "35%",
            "label": "Execute",
        },
        review_status="reviewed",
        evidence_count=2,
    )

    rows = LiveRaidEncounterProjectionService._clock_events((threshold_only, timed))

    assert len(rows) == 1
    assert rows[0].start_seconds == 15
    assert rows[0].label == "Portal team ready"


def test_live_raid_selected_encounter_survives_pull_start(tmp_path):
    state = RaidSectionStateService(tmp_path / "raid_section_state.json")

    state.set_selected_encounter_id("plan-1", "nahviintaas")
    started = state.start_pull("plan-1")

    assert started["encounter_id"] == "nahviintaas"
    assert state.selected_encounter_id("plan-1") == "nahviintaas"


def test_live_raid_page_has_encounter_driven_projection():
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    assert "self.encounter_combo" in source
    assert 'self.encounter_combo.addItem("Encounter: Trial / General", "")' in source
    assert "self.encounter_projection.encounters_for_trial(plan.trial_id)" in source
    assert "self.user_state.set_selected_encounter_id" in source
    assert "self._render_encounter_context()" in source
    assert "self.timeline_text" in source
    assert "self.encounter_checklist_label" in source


def test_live_raid_current_callouts_use_condition_markers():
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    assert "for condition in context.condition_events" in source
    assert '"THRESHOLD" if role == "threshold" else "PLAN"' in source
    assert "for event in context.clock_events" in source
    assert "self.timeline_text" in source
