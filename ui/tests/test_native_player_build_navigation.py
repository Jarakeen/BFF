from pathlib import Path


def test_personnel_records_natively_open_selected_player_builds() -> None:
    roster = Path("ui/themed_roster_page.py").read_text(encoding="utf-8")
    main_window = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert 'QPushButton("Open Builds")' in roster
    assert "self.table.itemDoubleClicked.connect" in roster
    assert "member = self.roster_service.get_member(int(member_id))" in roster
    assert "gamertag = str(member.PlayerName or" in roster
    assert "opener(gamertag)" in roster
    assert "def _open_player_builds(self, gamertag: str)" in main_window
    assert 'self.show_page("console:2")' in main_window


def test_builds_page_natively_filters_character_builds_by_gamertag() -> None:
    source = Path("ui/builds_page.py").read_text(encoding="utf-8")

    assert 'getattr(build, "Gamertag", "")' in source
    assert "matching_indexes" in source
    assert "character or 'Unnamed Character'" in source
    assert "build_name or 'Default'" in source
    assert "item.setData(Qt.ItemDataRole.UserRole, index)" in source
    assert "self.selected_index = index" in source
    assert "def show_player_builds(self, gamertag: str)" in source


def test_normal_builds_navigation_natively_clears_player_filter() -> None:
    main_window = Path("ui/main_window.py").read_text(encoding="utf-8")
    builds = Path("ui/builds_page.py").read_text(encoding="utf-8")

    show_page = main_window.split("def show_page(self, page_name: str):", 1)[1]
    assert 'if page_name == "console:2":' in show_page
    assert "clear_player_build_filter" in show_page
    assert "def clear_player_build_filter(self) -> None:" in builds


def test_obsolete_player_build_navigation_installer_is_not_composed() -> None:
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "player_build_navigation_support" not in bootstrap


def test_phase14_exact_build_navigation_clears_stale_library_filters() -> None:
    source = Path("ui/phase14_builds_command_center_support.py").read_text(encoding="utf-8")

    assert "def _reset_library_filters(page, *, mode: str = \"All\") -> None:" in source
    assert "search.clear()" in source
    assert '"phase14_class_filter"' in source
    assert '"phase14_role_filter"' in source
    assert '"phase14_content_filter"' in source
    assert 'wanted_tab = "Comp Builds" if comp_kind == "comp" else "All"' in source
    assert "_reset_library_filters(self, mode=wanted_tab)" in source


def test_phase14_player_build_navigation_resets_library_mode_before_filtering_player() -> None:
    source = Path("ui/phase14_builds_command_center_support.py").read_text(encoding="utf-8")

    assert "original_show_player_builds = BuildsPage.show_player_builds" in source
    assert "def show_player_builds_phase14(self, gamertag: str) -> None:" in source
    assert '_reset_library_filters(self, mode="All")' in source
    assert "original_show_player_builds(self, gamertag)" in source
    assert "BuildsPage.show_player_builds = show_player_builds_phase14" in source
