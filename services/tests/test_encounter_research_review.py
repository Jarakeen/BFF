from __future__ import annotations

from pathlib import Path

import pytest

from services.encounter_research_review import (
    candidate_source_preview,
    candidate_value_text,
    parse_candidate_value,
    update_candidate_value,
)
from services.encounter_research_store import EncounterResearchStore


def _store_with_candidate(tmp_path: Path) -> tuple[EncounterResearchStore, str]:
    source = tmp_path / "guide.md"
    source.write_text(
        "Intro line.\n"
        "Phase 2 begins at 50% health.\n"
        "Interrupt the channel.\n",
        encoding="utf-8",
    )
    store = EncounterResearchStore(tmp_path / "data")
    store.import_path(
        source,
        content_hint="rockgrove",
        encounter_hint="xalvakka",
        language="en",
    )
    candidate = next(
        row for row in store.candidates()
        if row.fact_type == "transition" and row.fact_key == "health_threshold"
    )
    return store, candidate.candidate_id


def test_candidate_value_json_round_trip_and_update_preserves_evidence(tmp_path: Path) -> None:
    store, candidate_id = _store_with_candidate(tmp_path)
    before = next(row for row in store.candidates() if row.candidate_id == candidate_id)

    parsed = parse_candidate_value('{"threshold": "49%", "approximate": true}')
    updated = update_candidate_value(store, candidate_id, parsed)

    assert updated.value == {"threshold": "49%", "approximate": True}
    assert updated.evidence_text == before.evidence_text
    assert '"approximate": true' in candidate_value_text(updated)


def test_invalid_candidate_value_json_is_rejected_without_mutation(tmp_path: Path) -> None:
    store, candidate_id = _store_with_candidate(tmp_path)
    before = next(row for row in store.candidates() if row.candidate_id == candidate_id)

    with pytest.raises(ValueError, match="not valid JSON"):
        parse_candidate_value('{"threshold":')

    after = next(row for row in store.candidates() if row.candidate_id == candidate_id)
    assert after.value == before.value


def test_source_preview_marks_evidence_line_and_context(tmp_path: Path) -> None:
    store, candidate_id = _store_with_candidate(tmp_path)

    preview = candidate_source_preview(store, candidate_id, context_lines=1)

    assert preview.source_name == "guide.md"
    assert preview.language == "en"
    assert "  1: Intro line." in preview.text
    assert "> 2: Phase 2 begins at 50% health." in preview.text
    assert "  3: Interrupt the channel." in preview.text


def test_map_preview_does_not_attempt_text_extraction(tmp_path: Path) -> None:
    source = tmp_path / "positioning.png"
    source.write_bytes(b"fake")
    store = EncounterResearchStore(tmp_path / "data")
    store.import_path(source, encounter_hint="reef_guardian")
    candidate_id = store.candidates()[0].candidate_id

    preview = candidate_source_preview(store, candidate_id)

    assert preview.source_type == "raid_map"
    assert "text extraction is not performed" in preview.text
