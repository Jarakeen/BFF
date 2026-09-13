from pathlib import Path


def test_roster_intake_carries_players_classes_and_roles_into_comp_maker():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert 'QTableWidgetItem("PLAYER")' in source
    assert 'getattr(member, "EsoClass"' in source
    assert 'getattr(member, "PrimaryRole"' in source
    assert "class_combo.setCurrentIndex(index)" in source
    assert "page._load_flexible(show_status=False)" in source
    assert "CompBuilderPage.apply_roster_team_context = apply_roster_team_context" in source


def test_roster_intake_matches_dd_and_places_known_roles_before_unresolved():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert 'if "dd" in words:' in source
    assert 'return "damage"' in source
    assert "known = [member for member in members" in source
    assert "unknown = [member for member in members" in source
    assert "if _row_role(page, r) == wanted" in source


def test_send_to_comp_maker_uses_roster_intake_bridge():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "comp.apply_roster_team_context(team_name, members)" in source
    assert "assignment_actions._send_to_comp_maker = _send_roster_team_to_comp" in source


def test_assignments_attention_card_header_is_hidden_but_card_remains():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "card.header.hide()" in source
    assert 'card.setProperty("flatActionCard", True)' in source


def test_roster_intake_installs_after_assignment_actions():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_comp_builder_roster_intake_support()" in source
    assert source.index("install_roster_assignment_action_support()") < source.index(
        "install_comp_builder_roster_intake_support()"
    )
