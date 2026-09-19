from pathlib import Path


def test_phase14_team_health_uses_canonical_comp_state_not_visible_row_projection() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    health = source.split("def _refresh_health(page)", 1)[1].split(
        "def _refresh_shell(page)", 1
    )[0]
    assert 'state = getattr(page, "_comp_plan_state", None)' in health
    assert "health = _cached_comp_health(page, state)" in health
    assert "coverage_from_candidate_rows" not in health
    assert "_effective_coverage_rows(page)" not in health
    assert "for gear in _effective_sets_for_row(page, row):" not in health
    assert "def _effective_sets_for_row" not in source
    assert "def _effective_coverage_rows" not in source
    assert "def _materialize_visible_recommendations" not in source


def test_phase14_recruit_health_uses_canonical_open_player_and_gear_gaps() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")

    health = source.split("def _refresh_health(page)", 1)[1].split(
        "def _refresh_shell(page)", 1
    )[0]
    assert "health.open_gear_seats" in health
    assert "health.open_player_seats" in health
    assert "open player seat(s)" in health
    assert "already have planned gear" in health
    assert "_effective_sets_for_row(page, row)" not in health
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
    assert "_persist_generated_comp_plan_to_raid_plan" not in save
    assert "save_generated_plan" not in save
    assert "persist_legacy" not in save


def test_raid_plan_comp_handoff_filters_manual_picker_to_five_piece_sets() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    handoff = source.split("def _bind_plan_comp_builder", 1)[1].split(
        "def _open_plan_comp_builder", 1
    )[0]
    assert "from services.comp_builder_build_candidates import _five_piece_set_names" in handoff
    assert "_five_piece_set_names(get_data_dir() / \"eso.db\", planned)" in handoff
    assert "tuple(five_piece[:2])" in handoff
    assert ")[:2]" not in handoff


def test_team_health_covered_tile_hover_lists_required_effects_from_service() -> None:
    source = Path("ui/comp_builder_phase14_shell_support.py").read_text(encoding="utf-8")
    service = Path("services/comp_plan_health_service.py").read_text(encoding="utf-8")

    assert "def required_effect_names() -> tuple[str, ...]:" in service
    build = source.split("def _build_health(page, card: FoundryCard) -> None:", 1)[1].split(
        "def _install_shell", 1
    )[0]
    assert "from services.comp_plan_health_service import required_effect_names" in build
    assert "required = required_effect_names()" in build
    assert "Team Health currently measures these default-required planned effects:" in build
    assert "tile.setToolTip(tooltip)" in build
    assert "value.setToolTip(tooltip)" in build
    assert "detail.setToolTip(tooltip)" in build
