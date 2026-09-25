from __future__ import annotations

import json
from pathlib import Path

from models.build_model import BuildRoster
from services import canonical_build_bridge as bridge_module
from services import user_data_migration_service as migration_module
from services.build_service import BuildService


def test_application_build_service_migrates_json_then_writes_only_user_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    user_dir = tmp_path / "user_data"
    data_dir.mkdir()
    user_dir.mkdir()
    user_db = user_dir / "foundrydock.db"

    builds_path = data_dir / "builds.json"
    characters_path = data_dir / "characters.json"
    builds_path.write_text('{"Members": []}', encoding="utf-8")
    characters_path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "players": [{"player_id": "p1", "gamertag": "Rikbacon"}],
                "characters": [
                    {
                        "character_id": "c1",
                        "player_id": "p1",
                        "name": "Tanky",
                        "gamertag": "Rikbacon",
                        "eso_class": "Dragonknight",
                    }
                ],
                "builds": [
                    {
                        "build_id": "b1",
                        "character_id": "c1",
                        "name": "Main Tank",
                        "payload": {
                            "Name": "Tanky",
                            "Gamertag": "Rikbacon",
                            "BuildName": "Main Tank",
                            "Armor": {"Chest": {"Set": "Pearlescent Ward"}},
                        },
                    }
                ],
                "team_assignments": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bridge_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(bridge_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(migration_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "ensure_user_database", lambda: user_db)

    original_builds = builds_path.read_bytes()
    original_characters = characters_path.read_bytes()

    service = BuildService(builds_path)
    roster = service.load()

    assert len(roster.Members) == 1
    assert roster.Members[0].BuildName == "Main Tank"
    assert user_db.is_file()

    # After migration, legacy files are no longer runtime authorities.
    builds_path.write_text('{"Members": []}', encoding="utf-8")
    characters_path.write_text('{"schema_version": 4, "players": [], "characters": [], "builds": [], "team_assignments": []}', encoding="utf-8")
    reloaded = service.load()
    assert len(reloaded.Members) == 1
    assert reloaded.Members[0].BuildName == "Main Tank"

    # Restore the migration inputs only to prove save does not rewrite them.
    builds_path.write_bytes(original_builds)
    characters_path.write_bytes(original_characters)
    service.save(BuildRoster(Members=list(roster.Members)))

    assert builds_path.read_bytes() == original_builds
    assert characters_path.read_bytes() == original_characters


def test_application_empty_projection_cannot_erase_canonical_saved_builds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    user_dir = tmp_path / "user_data"
    data_dir.mkdir()
    user_dir.mkdir()
    user_db = user_dir / "foundrydock.db"
    builds_path = data_dir / "builds.json"
    characters_path = data_dir / "characters.json"
    builds_path.write_text('{"Members": []}', encoding="utf-8")
    characters_path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "players": [{"player_id": "p1", "gamertag": "Rikbacon"}],
                "characters": [
                    {
                        "character_id": "c1",
                        "player_id": "p1",
                        "name": "Bacon",
                        "gamertag": "Rikbacon",
                        "eso_class": "Sorcerer",
                    }
                ],
                "builds": [
                    {
                        "build_id": "b1",
                        "character_id": "c1",
                        "name": "Rik — Sorcerer Tank",
                        "payload": {
                            "Name": "Bacon",
                            "Gamertag": "Rikbacon",
                            "BuildName": "Rik — Sorcerer Tank",
                        },
                    }
                ],
                "team_assignments": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bridge_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(bridge_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(migration_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "ensure_user_database", lambda: user_db)

    service = BuildService(builds_path)
    assert len(service.load().Members) == 1

    # A stale/filtered UI projection is not an explicit delete command.
    service.save(BuildRoster())

    catalog = service.canonical.load_catalog()
    assert [row["build_id"] for row in catalog["builds"]] == ["b1"]
    assert len(service.load().Members) == 1
    assert service.load().Members[0].BuildName == "Rik — Sorcerer Tank"


def test_application_forbids_destructive_sync_from_roster(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    user_dir = tmp_path / "user_data"
    data_dir.mkdir()
    user_dir.mkdir()
    user_db = user_dir / "foundrydock.db"
    builds_path = data_dir / "builds.json"
    characters_path = data_dir / "characters.json"
    builds_path.write_text('{"Members": []}', encoding="utf-8")
    characters_path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "players": [],
                "characters": [],
                "builds": [],
                "team_assignments": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bridge_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(bridge_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(migration_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "ensure_user_database", lambda: user_db)

    service = BuildService(builds_path)

    import pytest

    with pytest.raises(RuntimeError, match="Destructive sync_from_roster is forbidden"):
        service.canonical.sync_from_roster(BuildRoster())


def test_application_save_catalog_cannot_implicitly_delete_saved_build(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    user_dir = tmp_path / "user_data"
    data_dir.mkdir()
    user_dir.mkdir()
    user_db = user_dir / "foundrydock.db"
    builds_path = data_dir / "builds.json"
    characters_path = data_dir / "characters.json"
    builds_path.write_text('{"Members": []}', encoding="utf-8")
    characters_path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "players": [],
                "characters": [],
                "builds": [],
                "team_assignments": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bridge_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(bridge_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(migration_module, "get_user_database_path", lambda: user_db)
    monkeypatch.setattr(migration_module, "ensure_user_database", lambda: user_db)

    service = BuildService(builds_path)
    service.save(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Bacon",
                    Gamertag="Rikbacon",
                    BuildName="Rik Sorcerer Tank",
                )
            ]
        )
    )
    catalog = service.canonical.load_catalog()
    assert len(catalog["builds"]) == 1

    import pytest

    projected = dict(catalog)
    projected["builds"] = []
    with pytest.raises(RuntimeError, match="implicitly delete Saved Build"):
        service.canonical.save_catalog(projected)

    assert len(service.canonical.load_catalog()["builds"]) == 1


def test_copy_build_persists_with_new_id_and_preserves_source(tmp_path: Path) -> None:
    from models.build_model import BuildRoster, PlayerBuild
    from services.build_reuse_service import BuildReuseService
    from services.build_service import BuildService

    builds_path = tmp_path / "data" / "builds.json"
    service = BuildService(builds_path)
    catalog_service = service.canonical.catalog_service
    catalog = catalog_service.new_catalog()
    catalog["players"] = [
        {"player_id": "source-player", "gamertag": "Jarakeen"},
        {"player_id": "dest-player", "gamertag": "OtherPlayer"},
    ]
    catalog["characters"] = [
        {"character_id": "source-character", "player_id": "source-player", "name": "Magrat", "gamertag": "Jarakeen", "eso_class": "Warden"},
        {"character_id": "dest-character", "player_id": "dest-player", "name": "Maeve", "gamertag": "OtherPlayer", "eso_class": "Warden"},
    ]
    source = PlayerBuild(
        Name="Magrat", Gamertag="Jarakeen", BuildName="SW Healer",
        EsoClass="Warden", Role="Healer", PlayerId="source-player",
        CharacterId="source-character", BuildId="source-build",
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
    )
    service.save(BuildRoster(Members=[source]))
    before = catalog_service.load_strict()
    source_before = next(row for row in before["builds"] if row["build_id"] == "source-build")

    copied = BuildReuseService.copy_build(
        source,
        destination_name="Maeve",
        destination_gamertag="OtherPlayer",
        destination_class="Warden",
        destination_player_id="dest-player",
        destination_character_id="dest-character",
        new_build_name="SW Healer Copy",
    ).build
    service.save(BuildRoster(Members=[copied]))

    after = catalog_service.load_strict()
    assert len(after["builds"]) == 2
    assert next(row for row in after["builds"] if row["build_id"] == "source-build") == source_before
    copied_rows = [row for row in after["builds"] if row["build_id"] != "source-build"]
    assert len(copied_rows) == 1
    assert copied_rows[0]["build_id"]
    assert copied_rows[0]["build_id"] != "source-build"
    assert copied_rows[0]["character_id"] == "dest-character"
