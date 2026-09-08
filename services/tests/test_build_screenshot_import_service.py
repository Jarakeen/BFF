from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.build_screenshot_import_service import BuildScreenshotImportService


def _image(path: Path, payload: bytes = b"fake-image") -> Path:
    path.write_bytes(payload)
    return path


def test_stage_copies_armory_and_character_images_and_writes_manifest(tmp_path: Path) -> None:
    service = BuildScreenshotImportService(tmp_path / "imports")
    armory = _image(tmp_path / "armory.png", b"armory")
    character = _image(tmp_path / "character.jpg", b"character")

    intake = service.stage(armory_image=armory, character_image=character)

    folder = tmp_path / "imports" / intake.intake_id
    assert (folder / "armory.png").read_bytes() == b"armory"
    assert (folder / "character.jpg").read_bytes() == b"character"

    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "awaiting_analysis"
    assert manifest["recognition"]["status"] == "awaiting_analysis"
    assert manifest["recommended_capture_pair"] == ["armory", "character"]
    assert manifest["armory_images"] == [str(folder / "armory.png")]


def test_stage_keeps_multiple_armory_subviews_with_one_character_sheet(tmp_path: Path) -> None:
    service = BuildScreenshotImportService(tmp_path / "imports")
    equipment = _image(tmp_path / "equipment.png", b"equipment")
    skills = _image(tmp_path / "skills.png", b"skills")
    champion = _image(tmp_path / "champion.png", b"champion")
    character = _image(tmp_path / "character.png", b"character")

    intake = service.stage(
        armory_images=[equipment, skills, champion],
        character_image=character,
    )

    folder = tmp_path / "imports" / intake.intake_id
    assert (folder / "armory-01.png").read_bytes() == b"equipment"
    assert (folder / "armory-02.png").read_bytes() == b"skills"
    assert (folder / "armory-03.png").read_bytes() == b"champion"
    assert len(intake.armory_images) == 3

    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_files"]["armory"] == [
        str(equipment), str(skills), str(champion)
    ]
    assert manifest["recommended_capture_set"] == [
        "armory_equipment",
        "armory_skills",
        "armory_champion",
        "character_sheet",
    ]


def test_pending_returns_only_waiting_intakes(tmp_path: Path) -> None:
    service = BuildScreenshotImportService(tmp_path / "imports")
    armory = _image(tmp_path / "armory.png")
    character = _image(tmp_path / "character.png")
    intake = service.stage(armory_image=armory, character_image=character)

    pending = service.pending()
    assert [row.intake_id for row in pending] == [intake.intake_id]
    assert pending[0].armory_images == (pending[0].armory_image,)

    manifest_path = tmp_path / "imports" / intake.intake_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "reviewed"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert service.pending() == []


def test_stage_rejects_missing_or_unsupported_files(tmp_path: Path) -> None:
    service = BuildScreenshotImportService(tmp_path / "imports")
    good = _image(tmp_path / "character.png")

    with pytest.raises(FileNotFoundError, match="Armory screenshot"):
        service.stage(armory_image=tmp_path / "missing.png", character_image=good)

    bad = _image(tmp_path / "armory.txt")
    with pytest.raises(ValueError, match="must be one of"):
        service.stage(armory_image=bad, character_image=good)

    with pytest.raises(ValueError, match="at least one Armory"):
        service.stage(character_image=good)
