from pathlib import Path


def test_character_panel_avatar_is_player_owned() -> None:
    source = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert 'self.setWindowTitle("Choose Player Avatar")' in source
    assert 'catalog.set_player_avatar(' in source
    assert 'str(player.get("avatar_path") or character.get("avatar_path") or "")' in source
    assert 'self._active_avatar_player_id' in source
    assert 'catalog.set_character_avatar(' not in source


def test_avatar_assets_ship_in_release() -> None:
    manifest = Path("packaging/release_manifest.py").read_text(encoding="utf-8")
    assert '("assets/avatar", "assets/avatar")' in manifest
