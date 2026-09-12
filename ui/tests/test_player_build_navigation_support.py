from pathlib import Path

from ui import player_build_navigation_support


def test_personnel_records_open_selected_player_builds() -> None:
    source = Path(player_build_navigation_support.__file__).read_text(encoding="utf-8")

    assert 'QPushButton("Open Builds")' in source
    assert "self.table.itemDoubleClicked.connect" in source
    assert "self._open_selected_player_builds()" in source
    assert "member = self.roster_service.get_member(int(member_id))" in source
    assert "gamertag = _text(member.PlayerName)" in source
    assert "opener(gamertag)" in source


def test_builds_page_filters_character_build_list_by_gamertag() -> None:
    source = Path(player_build_navigation_support.__file__).read_text(encoding="utf-8")

    assert 'getattr(self, "Gamertag", "")' not in source
    assert 'getattr(build, "Gamertag", "")' in source
    assert "matching_indexes" in source
    assert 'label = f"{character} — {build_name}"' in source
    assert "item.setData(Qt.ItemDataRole.UserRole, index)" in source
    assert "self.selected_index = index" in source


def test_normal_builds_navigation_clears_player_filter() -> None:
    source = Path(player_build_navigation_support.__file__).read_text(encoding="utf-8")

    assert 'if page_name == "console:2":' in source
    assert "clear_player_build_filter" in source
    assert 'original_show_page(self, "console:2")' in source
    assert "show_player(gamertag)" in source
