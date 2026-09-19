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
