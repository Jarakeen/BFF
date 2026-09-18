from pathlib import Path


def test_roster_intake_carries_players_classes_and_roles_into_comp_maker():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert 'QTableWidgetItem("PLAYER")' in source
    assert 'getattr(member, "EsoClass"' in source
    assert 'getattr(member, "PrimaryRole"' in source
    assert "class_combo.setCurrentIndex(index)" in source
    assert "_load_roster_shape(page, group_size)" in source
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

    assert "comp.apply_roster_team_context(" in source
    assert "encounter_id=encounter_id" in source
    assert "encounter_name=encounter_name" in source
    assert "assignments=assignments" in source
    assert "assignment_actions._send_to_comp_maker = _send_roster_team_to_comp" in source


def test_assignments_attention_card_header_is_hidden_but_card_remains():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "card.header.hide()" in source
    assert 'card.setProperty("flatActionCard", True)' in source


def test_roster_intake_installs_after_assignment_actions():
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "install_comp_builder_roster_intake_support()" in source
    assert source.index("install_roster_assignment_action_support()") < source.index(
        "install_comp_builder_roster_intake_support()"
    )


def test_roster_intake_preserves_four_or_twelve_player_group_shape():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "return 4 if len(tuple(members)) <= 4 else 12" in source
    assert "flexible_raid_slots(group_size)" in source
    assert "page._comp_group_size = group_size" in source
    assert "_load_roster_shape(page, group_size)" in source


def test_roster_intake_treats_recruit_as_open_prescription_slot():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "def _is_recruit_member(member) -> bool:" in source
    assert 'value == "recruit"' in source
    assert "page._comp_roster_member_by_slot[slot_name] = None if _is_recruit_member(member) else member" in source


def test_roster_intake_places_player_first_in_visible_table():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "header.visualIndex(PLAYER_COLUMN)" in source
    assert "header.moveSection(visual_index, 0)" in source


def test_roster_intake_accepts_explicit_four_or_twelve_player_context():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "group_size: int | None = None" in source
    assert "group_size = 4 if group_size == 4 else 12 if group_size == 12" in source


def test_comp_builder_accepts_direct_pasted_team_list():
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")
    controls = Path("ui/comp_builder_main_controls_support.py").read_text(encoding="utf-8")

    assert "def open_team_list_dialog(page) -> None:" in source
    assert '"One player per line. Use Recruit for any open spot."' in source
    assert "group_size = 4 if len(names) <= 4 else 12" in source
    assert 'QPushButton("Load Team List")' in controls
    assert 'generate.setText("Recommend Team")' in controls
    assert 'apply_chair.setText("Use Selected Build")' in controls
