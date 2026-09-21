from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_live_raid_start_pull_captures_selected_encounter() -> None:
    source = _source("ui/city_live_raid_page.py")
    start = source[
        source.index("    def _start_pull")
        : source.index("    def _pause_notes")
    ]

    assert "encounter_id=_clean(self.encounter_combo.currentData())" in start


def test_live_raid_recent_events_include_durable_attempt_history() -> None:
    source = _source("ui/city_live_raid_page.py")
    refresh = source[
        source.index("    def _refresh_events")
        : source.index("    def _save_run_notes")
    ]

    assert "self.user_state.attempt_history(self._plan.plan_id)" in refresh
    assert 'f"ATTEMPT #{row.attempt}' in refresh
    assert "self._encounter_label(row.encounter_id)" in refresh
    assert "self._duration_label(row.duration_seconds)" in refresh


def test_live_raid_review_note_carries_attempt_encounter_identity() -> None:
    source = _source("ui/city_live_raid_page.py")
    save = source[
        source.index("    def _save_run_notes")
        : source.index("    def _start_pull")
    ]

    assert "encounter_id=_clean(state.get(\"encounter_id\"))" in save
