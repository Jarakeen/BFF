from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.encounter_repository import EncounterNotFoundError, EncounterRepository, EncounterSourceError


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    bosses, evidence = tmp_path / "bosses", tmp_path / "evidence"
    bosses.mkdir(); evidence.mkdir()
    return bosses, evidence


def test_exact_id_lookup_links_evidence_by_declared_id_not_filename(tmp_path: Path):
    bosses, evidence = _roots(tmp_path)
    _write(bosses / "anything.json", {"id":"oaxiltso", "name":"Oaxiltso", "health":{}, "mechanics":[], "phases":[]})
    _write(evidence / "unrelated_name.json", {"encounter_id":"oaxiltso", "evidence":[]})
    repo = EncounterRepository(bosses, evidence)
    assert repo.encounter_ids() == ("oaxiltso",)
    assert repo.get("oaxiltso").encounter_id == "oaxiltso"
    with pytest.raises(EncounterNotFoundError): repo.get("Oaxiltso")


def test_duplicate_ids_are_rejected_deterministically(tmp_path: Path):
    bosses, evidence = _roots(tmp_path)
    _write(bosses / "a.json", {"id":"same"}); _write(bosses / "b.json", {"id":"same"})
    with pytest.raises(EncounterSourceError, match="Duplicate"):
        EncounterRepository(bosses, evidence)


def test_malformed_and_missing_identity_sources_fail_loudly(tmp_path: Path):
    bosses, evidence = _roots(tmp_path)
    (bosses / "bad.json").write_text("not json", encoding="utf-8")
    with pytest.raises(EncounterSourceError, match="Invalid"):
        EncounterRepository(bosses, evidence)


def test_duplicate_evidence_for_one_encounter_is_rejected(tmp_path: Path):
    bosses, evidence = _roots(tmp_path)
    _write(bosses / "boss.json", {"id":"boss"})
    _write(evidence / "a.json", {"encounter_id":"boss", "evidence":[]})
    _write(evidence / "b.json", {"encounter_id":"boss", "evidence":[]})
    with pytest.raises(EncounterSourceError, match="Duplicate"):
        EncounterRepository(bosses, evidence)
