from pathlib import Path

from ui import roster_player_alias_support


def test_personnel_alias_surface_supports_history_manual_aliases_and_merges() -> None:
    source = Path(roster_player_alias_support.__file__).read_text(encoding="utf-8")

    assert "Known Aliases" in source
    assert "Add Alias…" in source
    assert "Merge Duplicate Player…" in source
    assert "Existing Player Identity" in source
    assert "personnel_rename" in source
    assert "rename_collision" in source
    assert "MERGE THIS DUPLICATE" in source
    assert "merge_players(" in source


def test_roster_startup_installs_player_alias_support_after_other_roster_decorators() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "install_roster_player_alias_support" in source
    assert source.index("install_roster_assignment_usability_support()") < source.index(
        "install_roster_player_alias_support()"
    )
