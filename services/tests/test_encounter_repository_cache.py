from pathlib import Path

import services.encounter_repository as encounter_repository_module
from services.encounter_repository import EncounterRepository


def test_encounter_definition_is_cached_per_repository_instance(tmp_path, monkeypatch) -> None:
    boss_root = tmp_path / "bosses"
    evidence_root = tmp_path / "evidence"
    boss_root.mkdir()
    evidence_root.mkdir()
    (boss_root / "oaxiltso.json").write_text('{"id": "oaxiltso"}', encoding="utf-8")

    calls = {"load": 0, "overlay": 0}
    definition = object()

    def fake_load_encounter_definition(path: Path, *, evidence_packet_path=None):
        calls["load"] += 1
        return definition

    def fake_overlay_canonical_mechanics(value, database_path: Path):
        calls["overlay"] += 1
        return value

    monkeypatch.setattr(
        encounter_repository_module,
        "load_encounter_definition",
        fake_load_encounter_definition,
    )
    monkeypatch.setattr(
        encounter_repository_module,
        "_overlay_canonical_mechanics",
        fake_overlay_canonical_mechanics,
    )

    repository = EncounterRepository(
        boss_root=boss_root,
        evidence_root=evidence_root,
        database_path=tmp_path / "eso.db",
    )

    first = repository.get("oaxiltso")
    second = repository.get("oaxiltso")

    assert first is definition
    assert second is definition
    assert calls == {"load": 1, "overlay": 1}


def test_encounter_definition_cache_is_not_global(tmp_path, monkeypatch) -> None:
    boss_root = tmp_path / "bosses"
    evidence_root = tmp_path / "evidence"
    boss_root.mkdir()
    evidence_root.mkdir()
    (boss_root / "oaxiltso.json").write_text('{"id": "oaxiltso"}', encoding="utf-8")

    calls = {"load": 0}

    def fake_load_encounter_definition(path: Path, *, evidence_packet_path=None):
        calls["load"] += 1
        return object()

    monkeypatch.setattr(
        encounter_repository_module,
        "load_encounter_definition",
        fake_load_encounter_definition,
    )

    first_repository = EncounterRepository(
        boss_root=boss_root,
        evidence_root=evidence_root,
    )
    second_repository = EncounterRepository(
        boss_root=boss_root,
        evidence_root=evidence_root,
    )

    first_repository.get("oaxiltso")
    second_repository.get("oaxiltso")

    assert calls["load"] == 2
