from pathlib import Path


def test_merge_layout_fix_installs_after_merge_visibility_support() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")
    assert source.index("install_roster_team_merge_visibility_support()") < source.index(
        "install_roster_team_merge_layout_fix()"
    )


def test_merge_layout_fix_targets_foundry_card_body_row() -> None:
    source = Path("ui/roster_team_merge_layout_fix.py").read_text(encoding="utf-8")
    assert "card.body_layout" in source
    assert "destination_row.indexOf(delete_button)" in source
    assert "current_layout.removeWidget(merge_button)" in source
