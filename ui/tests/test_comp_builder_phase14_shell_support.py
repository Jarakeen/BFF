from pathlib import Path


def test_phase14_comp_builder_visible_shell_matches_approved_work_chat_contract() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '"Plan the team. Fill the gaps. Clear the content."' in source
    assert 'matrix.set_title("Recommended Team Plan")' in source
    assert 'details.set_title("Why This Plan")' in source
    assert 'coverage.set_title("Team Health")' in source
    assert 'generate.setText("Generate Team Plan")' in source
    assert 'load_team.setText("Load Team")' in source
    assert 'save.setText("Save Plan")' in source
    assert 'send.setText("Send to Roster")' in source


def test_phase14_comp_builder_brief_owns_required_controls() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '_context_box("TRIAL", page.goal_combo)' in source
    assert '_context_box("DIFFICULTY", page.difficulty_combo)' in source
    assert '_context_box("PLAN NAME", page.plan_name_input)' in source
    assert '_context_box("PLAN STYLE", style)' in source
    assert 'for size in (4, 12):' in source


def test_phase14_comp_builder_plan_table_is_player_first_and_role_grouped() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '"PLAYER"' in source
    assert '"ROLE / CLASS"' in source
    assert '"RECOMMENDED BUILD (SETS)"' in source
    assert '"KEY RESPONSIBILITY"' in source
    assert '"STATUS"' in source
    assert '("tank", "TANKS")' in source
    assert '("healer", "HEALERS")' in source
    assert '("damage", "DAMAGE")' in source


def test_phase14_comp_builder_why_panel_is_source_backed() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "candidate_support._chair_candidates(page, row)" in source
    assert "score_reasons" in source
    assert '"ALTERNATIVES"' in source
    assert "_candidate_source(candidate)" in source


def test_phase14_comp_builder_health_summarizes_coverage_duplicates_and_recruits() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert '("COVERED",' in source
    assert '("MISSING",' in source
    assert '("DUPLICATE",' in source
    assert '("RECRUIT NEED",' in source
    assert "polish.coverage_from_candidate_rows" in source
    assert "set_counts: Counter[str]" in source


def test_phase14_comp_builder_shell_installs_after_legacy_extensions() -> None:
    bootstrap = Path("ui/application_team_optimization_bootstrap.py").read_text(encoding="utf-8")

    assert "install_comp_builder_phase14_shell()" in bootstrap
    assert bootstrap.index("install_comp_builder_polish()") < bootstrap.index(
        "install_comp_builder_phase14_shell()"
    )
    assert bootstrap.index("install_coverage_group_effect_catalog_support()") < bootstrap.index(
        "install_comp_builder_phase14_shell()"
    )
