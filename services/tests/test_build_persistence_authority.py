from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.build_model import BuildRoster, PlayerBuild
from services.build_service import BuildService


def _roster() -> BuildRoster:
    return BuildRoster(
        Members=[
            PlayerBuild(
                Name="Magrat",
                Gamertag="Jarakeen",
                BuildName="DF Healer",
                EsoClass="Warden",
                Role="Healer",
                Mundus="The Ritual",
            )
        ]
    )


def test_build_service_methods_are_not_replaced_by_package_import() -> None:
    assert BuildService.load.__module__ == "services.build_service"
    assert BuildService.save.__module__ == "services.build_service"


def test_build_service_save_writes_canonical_catalog_and_compatibility_mirror(
    tmp_path: Path,
) -> None:
    builds_path = tmp_path / "builds.json"
    service = BuildService(builds_path)

    service.save(_roster())

    catalog_path = tmp_path / "characters.json"
    assert catalog_path.is_file()
    assert builds_path.is_file()

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["builds"]
    assert catalog["builds"][0]["legacy"]["BuildName"] == "DF Healer"

    mirror = json.loads(builds_path.read_text(encoding="utf-8"))
    assert mirror["Members"][0]["BuildName"] == "DF Healer"

    reloaded = service.load()
    assert len(reloaded.Members) == 1
    assert reloaded.Members[0].Name == "Magrat"
    assert reloaded.Members[0].BuildName == "DF Healer"


def test_corrupt_canonical_catalog_fails_closed_instead_of_falling_back(
    tmp_path: Path,
) -> None:
    builds_path = tmp_path / "builds.json"
    service = BuildService(builds_path)
    service.save(_roster())

    (tmp_path / "characters.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        service.load()


def test_corrupt_compatibility_mirror_fails_closed_when_catalog_has_no_builds(
    tmp_path: Path,
) -> None:
    builds_path = tmp_path / "builds.json"
    builds_path.write_text("{not-json", encoding="utf-8")

    service = BuildService(builds_path)

    with pytest.raises(json.JSONDecodeError):
        service.load()


def test_build_service_load_reconstructs_comp_build_from_canonical_record_metadata(
    tmp_path: Path,
) -> None:
    characters_path = tmp_path / "characters.json"
    characters_path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "players": [
                    {
                        "player_id": "player-1",
                        "gamertag": "Jarakeen",
                        "display_name": "Jarakeen",
                    }
                ],
                "characters": [
                    {
                        "character_id": "character-1",
                        "player_id": "player-1",
                        "name": "Magrat",
                        "gamertag": "Jarakeen",
                        "eso_class": "Warden",
                        "role": "Healer",
                    }
                ],
                "builds": [
                    {
                        "build_id": "comp-build-1",
                        "character_id": "character-1",
                        "name": "Performance Mode • Healer1",
                        "build_kind": "comp",
                        "source": {
                            "kind": "comp_maker",
                            "plan_id": "plan-1",
                            "plan_name": "Performance Mode",
                            "seat_id": "Healer1",
                        },
                        "payload": {
                            "BuildName": "Performance Mode • Healer1",
                            "PlannedGearSets": ["Spell Power Cure", "Pillager's Profit"],
                        },
                        "legacy": {
                            "BuildName": "Performance Mode • Healer1",
                            "PlannedGearSets": ["Spell Power Cure", "Pillager's Profit"],
                        },
                    }
                ],
                "team_assignments": [],
            }
        ),
        encoding="utf-8",
    )

    build = BuildService(tmp_path / "builds.json").load().Members[0]

    assert build.BuildId == "comp-build-1"
    assert build.BuildKind == "comp"
    assert build.CharacterId == "character-1"
    assert build.Name == "Magrat"
    assert build.Gamertag == "Jarakeen"
    assert build.EsoClass == "Warden"
    assert build.SourcePlanId == "plan-1"
    assert build.SourcePlanName == "Performance Mode"
    assert build.SourceSeatId == "Healer1"
    assert build.PlannedGearSets == ["Spell Power Cure", "Pillager's Profit"]
