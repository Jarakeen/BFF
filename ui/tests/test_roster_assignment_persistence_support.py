from pathlib import Path


def test_assignment_persistence_support_restores_and_saves_editable_fields():
    source = Path("ui/roster_assignment_persistence_support.py").read_text(encoding="utf-8")

    assert '"primary_assignment"' in source
    assert '"secondary_assignment"' in source
    assert '"gear_needed"' in source
    assert '"notes"' in source
    assert "get_member_assignment(member_id)" in source
    assert "set_member_assignment_field(member_id, field, value)" in source


def test_assignment_persistence_installs_after_team_filtering():
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "install_roster_assignment_persistence_support()" in source
    assert source.index("install_roster_team_assignment_filter_support()") < source.index(
        "install_roster_assignment_persistence_support()"
    )
