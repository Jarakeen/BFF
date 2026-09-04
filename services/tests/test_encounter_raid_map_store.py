from __future__ import annotations

from pathlib import Path

import pytest

from services.encounter_raid_map_store import EncounterRaidMapStore


def _image(path: Path, payload: bytes = b"fake-png") -> Path:
    path.write_bytes(payload)
    return path


def test_raid_maps_are_scoped_to_encounter_and_persisted(tmp_path: Path) -> None:
    store = EncounterRaidMapStore(tmp_path)
    source = _image(tmp_path / "strategy.png")

    record = store.import_map("xalvakka", source, label="Upper Floor")

    assert record.encounter_id == "xalvakka"
    assert record.label == "Upper Floor"
    assert store.resolve_path(record).is_file()
    assert store.list_maps("xalvakka") == (record,)
    assert store.list_maps("reef_guardian") == ()

    reloaded = EncounterRaidMapStore(tmp_path)
    assert reloaded.list_maps("xalvakka") == (record,)


def test_same_image_can_be_saved_to_different_bosses_without_cross_linking(tmp_path: Path) -> None:
    store = EncounterRaidMapStore(tmp_path)
    source = _image(tmp_path / "raid.webp")

    first = store.import_map("xalvakka", source)
    second = store.import_map("tideborn_taleria", source)

    assert first.map_id == second.map_id
    assert first.relative_path != second.relative_path
    assert store.resolve_path(first).is_file()
    assert store.resolve_path(second).is_file()


def test_removing_map_removes_only_selected_boss_copy(tmp_path: Path) -> None:
    store = EncounterRaidMapStore(tmp_path)
    source = _image(tmp_path / "raid.jpg")
    first = store.import_map("xalvakka", source)
    second = store.import_map("tideborn_taleria", source)

    assert store.remove_map("xalvakka", first.map_id) is True

    assert store.list_maps("xalvakka") == ()
    assert not store.resolve_path(first).exists()
    assert store.list_maps("tideborn_taleria") == (second,)
    assert store.resolve_path(second).exists()


def test_raid_map_store_rejects_non_image_and_path_like_encounter_ids(tmp_path: Path) -> None:
    store = EncounterRaidMapStore(tmp_path)
    source = tmp_path / "notes.txt"
    source.write_text("not an image", encoding="utf-8")

    with pytest.raises(ValueError, match="PNG, JPG, JPEG, or WebP"):
        store.import_map("xalvakka", source)

    with pytest.raises(ValueError, match="canonical id"):
        store.list_maps("../xalvakka")
