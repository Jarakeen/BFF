from __future__ import annotations

from pathlib import Path
import zipfile

from services.encounter_research_store import EncounterResearchStore


def test_import_text_source_registers_provenance_and_candidates(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source = tmp_path / "guide.md"
    source.write_text(
        "Phase 2 begins at 50% health. Interrupt the channel and move to the portal.\n",
        encoding="utf-8",
    )
    store = EncounterResearchStore(data_dir)

    imported = store.import_path(
        source,
        content_hint="rockgrove",
        encounter_hint="xalvakka",
        language="en",
    )

    assert len(imported) == 1
    row = imported[0]
    assert row.original_name == "guide.md"
    assert row.content_hint == "rockgrove"
    assert row.encounter_hint == "xalvakka"
    assert row.language == "en"
    assert len(row.sha256) == 64
    assert (data_dir / row.stored_path).is_file()

    candidates = store.candidates()
    assert {candidate.fact_type for candidate in candidates} >= {
        "phase",
        "transition",
        "interrupt",
        "positioning",
    }
    assert all(candidate.status == "pending" for candidate in candidates)


def test_duplicate_source_hash_is_not_registered_twice(tmp_path: Path) -> None:
    source = tmp_path / "guide.txt"
    source.write_text("Adds spawn at 75%.\n", encoding="utf-8")
    store = EncounterResearchStore(tmp_path / "data")

    first = store.import_path(source)
    second = store.import_path(source)

    assert first[0].source_id == second[0].source_id
    assert len(store.sources()) == 1


def test_zip_import_skips_unsafe_and_unsupported_members(tmp_path: Path) -> None:
    archive = tmp_path / "guides.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("trial/boss.md", "Phase 3 starts at 30%.\n")
        bundle.writestr("../escape.txt", "should not escape\n")
        bundle.writestr("trial/blob.exe", "nope")
    store = EncounterResearchStore(tmp_path / "data")

    rows = store.import_path(archive, content_hint="dreadsail_reef")

    assert len(rows) == 1
    assert rows[0].original_name == "trial/boss.md"
    assert rows[0].content_hint == "dreadsail_reef"


def test_map_import_becomes_review_candidate(tmp_path: Path) -> None:
    source = tmp_path / "positioning.png"
    source.write_bytes(b"not-real-image-but-store-is-format-level")
    store = EncounterResearchStore(tmp_path / "data")

    store.import_path(source, encounter_hint="reef_guardian")

    candidate = store.candidates()[0]
    assert candidate.fact_type == "map"
    assert candidate.encounter_id == "reef_guardian"
    assert candidate.value["stored_path"].endswith("positioning.png")


def test_review_status_changes_without_canonical_promotion(tmp_path: Path) -> None:
    source = tmp_path / "guide.txt"
    source.write_text("Interrupt the cast.\n", encoding="utf-8")
    store = EncounterResearchStore(tmp_path / "data")
    store.import_path(source)
    candidate = store.candidates()[0]

    updated = store.set_candidate_status(
        candidate.candidate_id,
        "approved",
        reviewer_note="Verified against second source later.",
    )

    assert updated.status == "approved"
    assert updated.reviewer_note == "Verified against second source later."
    assert store.counts()["approved"] == 1


def test_reviewer_can_assign_and_normalize_candidate_without_changing_evidence(tmp_path: Path) -> None:
    source = tmp_path / "guide.txt"
    source.write_text("Interrupt the cast.\n", encoding="utf-8")
    store = EncounterResearchStore(tmp_path / "data")
    store.import_path(source)
    candidate = store.candidates()[0]
    original_evidence = candidate.evidence_text
    original_value = candidate.value

    updated = store.update_candidate(
        candidate.candidate_id,
        content_id="dreadsail_reef",
        encounter_id="reef_guardian",
        fact_type="Interrupt",
        fact_key="Guardian Interrupt",
        reviewer_note="Boss assignment verified during review.",
    )

    assert updated.content_id == "dreadsail_reef"
    assert updated.encounter_id == "reef_guardian"
    assert updated.fact_type == "interrupt"
    assert updated.fact_key == "guardian interrupt"
    assert updated.reviewer_note == "Boss assignment verified during review."
    assert updated.evidence_text == original_evidence
    assert updated.value == original_value
