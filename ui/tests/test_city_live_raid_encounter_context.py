from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_live_raid_routes_canonical_encounter_context_into_operational_cards() -> None:
    source = _source("ui/city_live_raid_page.py")

    assert "LiveRaidEncounterProjectionService" in source
    assert "encounters_for_trial(plan.trial_id)" in source
    assert "context_for(" in source
    assert 'FoundryCard("Next 60 Seconds", "stopwatch")' in source
    assert "context.clock_events" in source
    assert "context.phase_lines" in source
    assert "context.condition_events" in source
    assert "context.callouts" in source
    assert "context.checklist" in source


def test_live_raid_timeline_never_claims_thresholds_are_clock_events() -> None:
    source = _source("ui/city_live_raid_page.py")

    assert "No reviewed wall-clock events are persisted for this encounter." in source
    assert "Threshold guide:" in source
    assert "event.start_seconds >= window_start" in source
    assert "event.start_seconds <= window_end" in source


def test_live_raid_encounter_phase_is_labeled_as_guide_not_observed_state() -> None:
    source = _source("ui/city_live_raid_page.py")

    assert 'self.phase_label.setText("Phase Guide\\nTrial / General")' in source
    assert '"Phase Guide\\n"' in source
    assert "OBSERVED = external telemetry (not connected)" in source
    assert "Current Phase\n" not in source[
        source.index("    def _render_encounter_context")
        : source.index("    def _render_plan")
    ]


def test_live_raid_clock_refresh_recomputes_next_sixty_second_window_during_pull() -> None:
    source = _source("ui/city_live_raid_page.py")
    clock = source[
        source.index("    def _refresh_clock")
        : source.index("    def _refresh_events")
    ]

    assert "datetime.now(timezone.utc)" in clock
    assert "self._render_encounter_context()" in clock
