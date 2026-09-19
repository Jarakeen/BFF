from pathlib import Path


def test_phase14_team_health_uses_effective_visible_chair_gear() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    assert "def _effective_sets_for_row(page, row: int)" in source
    assert "def _effective_coverage_rows(page)" in source
    assert "manual = _manual_sets_for_slot(page, slot)" in source
    assert "assigned = polish.coverage_from_candidate_rows(_effective_coverage_rows(page))" in source
    assert "for gear in _effective_sets_for_row(page, row):" in source


def test_phase14_recruit_health_separates_open_player_seats_from_gear_gaps() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    health = source.split("def _refresh_health(page)", 1)[1].split(
        "def _refresh_shell(page)", 1
    )[0]
    assert "has_gear = bool(_effective_sets_for_row(page, row))" in health
    assert "unresolved_gear = [row for row in recruits if not row[2]]" in health
    assert "open player seat(s)" in health
    assert "already have planned gear" in health
    assert "Recruit slot(s) need gear / setup" not in health


def test_phase14_save_plan_uses_canonical_state_without_silent_autofill() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    save = source.split("def _save_to_originating_raid_plan", 1)[1].split(
        "def _build_health", 1
    )[0]
    assert "try:" in save
    assert "except Exception as exc:" in save
    assert "Could not save Comp Builder plan:" in save
    assert 'getattr(page, "_comp_plan_state", None)' in save
    assert 'getattr(window, "_persist_comp_plan_state_to_raid_plan", None)' in save
    assert "_materialize_visible_recommendations(page)" not in save
    assert 'getattr(window, "_persist_generated_comp_plan_to_raid_plan",' in save


def test_raid_plan_comp_handoff_filters_manual_picker_to_five_piece_sets() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    handoff = source.split("def _bind_plan_comp_builder", 1)[1].split(
        "def _open_plan_comp_builder", 1
    )[0]
    assert "from services.comp_builder_build_candidates import _five_piece_set_names" in handoff
    assert "_five_piece_set_names(get_data_dir() / \"eso.db\", planned)" in handoff
    assert "tuple(five_piece[:2])" in handoff
    assert ")[:2]" not in handoff
