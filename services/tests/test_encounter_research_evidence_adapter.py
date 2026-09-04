from __future__ import annotations

from pathlib import Path

from services.encounter_research_store import EncounterResearchStore


def test_only_approved_boss_assigned_candidates_become_encounter_evidence(tmp_path: Path) -> None:
    assigned = tmp_path / "assigned.txt"
    assigned.write_text("Interrupt the channel.\n", encoding="utf-8")
    unassigned = tmp_path / "unassigned.txt"
    unassigned.write_text("Adds spawn.\n", encoding="utf-8")

    store = EncounterResearchStore(tmp_path / "data")
    store.import_path(assigned, encounter_hint="xalvakka")
    store.import_path(unassigned)

    candidates = store.candidates()
    assigned_candidate = next(row for row in candidates if row.encounter_id == "xalvakka")
    unassigned_candidate = next(row for row in candidates if not row.encounter_id)
    store.set_candidate_status(assigned_candidate.candidate_id, "approved")
    store.set_candidate_status(unassigned_candidate.candidate_id, "approved")

    evidence = store.approved_evidence()

    assert len(evidence) == 1
    row = evidence[0]
    assert row.encounter_id == "xalvakka"
    assert row.fact_type == "interrupt"
    assert row.fact_key == "interrupt"
    assert row.source_name == "assigned.txt"
    assert row.source_locator.startswith("encounter_research/sources/")
    assert len(row.source_revision) == 64
    assert row.source_family == row.source_revision


def test_pending_research_never_enters_existing_evidence_pipeline(tmp_path: Path) -> None:
    source = tmp_path / "guide.txt"
    source.write_text("Phase 2 begins at 50%.\n", encoding="utf-8")
    store = EncounterResearchStore(tmp_path / "data")
    store.import_path(source, encounter_hint="reef_guardian")

    assert store.approved_evidence() == ()
