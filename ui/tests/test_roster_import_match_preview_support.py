from pathlib import Path


def test_import_preview_adds_simple_match_column():
    source = Path("ui/roster_import_match_preview_support.py").read_text(encoding="utf-8")

    assert '_MATCH_COLUMN_TITLE = "Match"' in source
    assert 'return "Existing"' in source
    assert 'return "New Character"' in source
    assert 'return "New Build"' in source
    assert 'return "Needs Review"' in source
    assert "self.table.insertColumn(self._match_column)" in source
    assert "self.table.itemChanged.connect(refresh_match)" in source


def test_import_preview_matches_player_character_and_build_hierarchy():
    source = Path("ui/roster_import_match_preview_support.py").read_text(encoding="utf-8")

    assert "known_players" in source
    assert "known_characters" in source
    assert "known_builds" in source
    assert "character_exists" in source
    assert "A known person with a different/new toon is still one Personnel player" in source


def test_import_match_preview_installs_after_identity_resolution():
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "install_roster_import_match_preview_support()" in source
    assert source.index("install_roster_import_identity_resolution_support()") < source.index(
        "install_roster_import_match_preview_support()"
    )
