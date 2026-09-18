from __future__ import annotations

from services.build_catalog_service import BuildCatalogService


def test_player_avatar_persists_on_player_not_character(tmp_path) -> None:
    catalog = BuildCatalogService(tmp_path / "characters.json")
    catalog.save(
        {
            "schema_version": 4,
            "players": [
                {
                    "player_id": "player-1",
                    "gamertag": "Jarakeen",
                    "status": "Active",
                }
            ],
            "characters": [
                {
                    "character_id": "char-1",
                    "player_id": "player-1",
                    "name": "Magrat",
                    "gamertag": "Jarakeen",
                },
                {
                    "character_id": "char-2",
                    "player_id": "player-1",
                    "name": "Second Character",
                    "gamertag": "Jarakeen",
                },
            ],
            "builds": [],
            "team_assignments": [],
        }
    )

    saved = catalog.set_player_avatar(
        player_id="player-1",
        avatar_path="assets/avatar/raven.webp",
    )

    assert saved is not None
    assert saved["avatar_path"] == "assets/avatar/raven.webp"
    reloaded = catalog.get_player("player-1")
    assert reloaded is not None
    assert reloaded["avatar_path"] == "assets/avatar/raven.webp"
    assert "avatar_path" not in catalog.get_character("char-1")
    assert "avatar_path" not in catalog.get_character("char-2")
