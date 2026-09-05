from pathlib import Path


EXPECTED_TRIALS = (
    "Sunspire",
    "Rockgrove",
    "Dreadsail Reef",
    "Sanity's Edge",
    "Lucent Citadel",
    "Ossein Cage",
    "Cloudrest",
    "Kyne's Aegis",
    "Asylum Sanctorium",
    "Halls of Fabrication",
)


def test_comp_maker_trial_scope_contains_requested_endgame_trials() -> None:
    source = Path("services/comp_builder_trial_scope.py").read_text(encoding="utf-8")

    for trial in EXPECTED_TRIALS:
        assert f'"{trial}"' in source
    assert "COMP_MAKER_TRIALS" in source


def test_trial_scope_preserves_legacy_achievement_catalog_keys() -> None:
    source = Path("services/comp_builder_trial_scope.py").read_text(encoding="utf-8")

    assert '"Sunspire": "Godslayer"' in source
    assert '"Rockgrove": "Planebreaker"' in source
    assert '"Dreadsail Reef": "Swashbuckler Supreme"' in source
    assert '"Cloudrest": "Gryphon Heart"' in source
    assert '"Kyne\'s Aegis": "Dawnbringer"' in source
    assert '"Asylum Sanctorium": "Immortal Redeemer"' in source
    assert '"Halls of Fabrication": "Tick-Tock Tormentor"' in source


def test_comp_maker_visible_selector_is_replaced_with_trials() -> None:
    source = Path("ui/comp_builder_trial_flow_support.py").read_text(encoding="utf-8")

    assert "page.goal_combo.clear()" in source
    assert "page.goal_combo.addItems(COMP_MAKER_TRIALS)" in source
    assert 'label.setText("TRIAL")' in source


def test_trial_selection_refreshes_local_candidates_and_live_esologs() -> None:
    source = Path("ui/comp_builder_trial_flow_support.py").read_text(encoding="utf-8")

    assert "candidate_support._refresh_candidates(page)" in source
    assert "picker_support._refresh_picker(page)" in source
    assert "esologs_support._refresh_live_esologs(page)" in source
    assert "page.goal_combo.currentTextChanged.connect" in source
    assert "QTimer.singleShot" in source


def test_trial_first_flow_routes_candidate_catalog_through_legacy_goal_mapping() -> None:
    source = Path("ui/comp_builder_trial_flow_support.py").read_text(encoding="utf-8")

    assert "goal = default_goal_for_trial(trial_name)" in source
    assert "candidates_for_chair(" in source
    assert "candidate_support._chair_candidates = _chair_candidates_for_selected_trial" in source


def test_trial_first_flow_routes_esologs_by_visible_trial_name() -> None:
    source = Path("ui/comp_builder_trial_flow_support.py").read_text(encoding="utf-8")

    assert "esologs_support._current_trial = (" in source
    assert "trial_for_selection(page.goal_combo.currentText())" in source


def test_comp_maker_final_action_uses_send_comp_to_roster_language() -> None:
    source = Path("ui/comp_builder_trial_flow_support.py").read_text(encoding="utf-8")

    assert 'send.setText("Send Comp to Roster")' in source
    assert 'refresh.setText("Refresh Build Sources")' in source
    assert "apply_observed.hide()" in source


def test_trial_flow_installs_after_candidate_and_assignment_surfaces() -> None:
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    candidates = installer.index("install_comp_builder_build_candidates()")
    picker = installer.index("install_comp_builder_candidate_picker()")
    assignment = installer.index("install_comp_builder_assignment_cue()")
    trial_flow = installer.index("install_comp_builder_trial_flow()")
    layout = installer.index("install_comp_builder_layout()")

    assert candidates < picker < assignment < trial_flow < layout
