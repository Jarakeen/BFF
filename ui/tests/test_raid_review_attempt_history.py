from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_review_indexes_attempts_even_without_notes() -> None:
    source = _source("ui/raid_review_page.py")

    assert "attempts = self.state.all_attempt_history()" in source
    assert "notes_by_attempt" in source
    assert '"notes": _clean(note.get("notes")) if note else ""' in source
    assert '"No run note was saved for this attempt."' in source


def test_review_groups_attempts_by_date_trial_and_encounter() -> None:
    source = _source("ui/raid_review_page.py")

    assert "date_item" in source
    assert 'trial_key = f"trial:{trial}"' in source
    assert 'encounter_key = f"encounter:{trial}:{encounter}"' in source
    assert "encounter_item.addChild(item)" in source


def test_review_uses_canonical_encounter_name_when_available() -> None:
    source = _source("ui/raid_review_page.py")

    assert "EncounterBossGuideService(DEFAULT_DATABASE)" in source
    assert "self.guide_service.get(key).name" in source
    assert 'key.replace("_", " ").replace("-", " ").title()' in source


def test_review_labels_note_presence_without_requiring_it() -> None:
    source = _source("ui/raid_review_page.py")

    assert 'label += " · NOTE"' in source
    assert '"Saved note" if has_note else "No saved note"' in source


def test_review_shows_per_encounter_attempt_summary_table() -> None:
    source = _source("ui/raid_review_page.py")

    assert 'FoundryCard("Encounter Summary", "compass")' in source
    assert '["TRIAL", "ENCOUNTER", "PULLS", "TIMED", "AVERAGE", "BEST", "NOTES"]' in source
    assert "summarize_encounter_attempts(attempts, notes)" in source
    assert "summary.average_duration_seconds" in source
    assert "summary.best_duration_seconds" in source
    assert "summary.note_count" in source
