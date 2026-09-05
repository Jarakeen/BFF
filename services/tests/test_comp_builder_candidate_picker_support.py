from pathlib import Path


def test_comp_maker_has_explicit_build_choice_selector() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(encoding="utf-8")

    assert 'page.comp_candidate_choice_combo = QComboBox()' in source
    assert 'setProperty("compCandidateChoice", True)' in source
    assert 'f"#{rank}  {candidate.name}  •  {source}  •  {candidate.score:.1f}"' in source
    assert "candidate.candidate_id" in source


def test_candidate_picker_stays_pinned_above_scrollable_esologs_catalog() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(encoding="utf-8")
    cue = Path("ui/comp_builder_assignment_cue_support.py").read_text(encoding="utf-8")

    assert 'picker_host.setProperty("compCandidatePickerHost", True)' in source
    assert "details.body_layout.insertWidget(0, picker_host)" in source
    assert "QScrollArea" not in source
    assert 'picker_host = getattr(page, "comp_candidate_picker_host", None)' in cue
    assert "picker_layout.insertWidget(1, cue)" in cue


def test_assign_build_uses_explicit_selected_candidate_not_implicit_top_rank() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(encoding="utf-8")

    assert "candidate_id = combo.currentData()" in source
    assert "if candidate.candidate_id == candidate_id" in source
    assert "candidate_support._set_candidate_for_row(page, row, candidate)" in source
    assert "Assigned {candidate.name} to {slot_name}" in source


def test_explicit_build_assignment_still_blocks_duplicate_saved_player() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(encoding="utf-8")

    assert "used_saved_players = candidate_support._used_saved_players(page)" in source
    assert "player_key = candidate_support._saved_player_key(candidate)" in source
    assert "if player_key and player_key in used_saved_players" in source
    assert "already assigned to another chair" in source


def test_candidate_picker_reuses_existing_authoritative_assignment_callback() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(encoding="utf-8")
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(encoding="utf-8")

    assert "candidate_support._apply_top_candidate = _apply_selected_candidate" in source
    assert "install_comp_builder_build_candidates()" in installer
    assert "install_comp_builder_candidate_picker()" in installer
    assert installer.index("install_comp_builder_build_candidates()") < installer.index(
        "install_comp_builder_candidate_picker()"
    )


def test_rylo_styles_explicit_build_choice_with_assignment_accent() -> None:
    source = Path("ui/comp_builder_rylo_support.py").read_text(encoding="utf-8")

    assert 'QLabel[compCandidateChoiceLabel="true"]' in source
    assert 'QComboBox[compCandidateChoice="true"]' in source
    assert "#B88A3C" in source
