from pathlib import Path


def test_comp_maker_receives_team_boss_and_effective_jobs() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "encounter_id: str = \"\"" in source
    assert "encounter_name: str = \"\"" in source
    assert "page._roster_team_context_assignments = assignments" in source
    assert "get_effective_assignment(" in source
    assert "raid jobs are carried over" in source


def test_comp_maker_keeps_role_chair_matching_separate_from_raid_job() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert "_match_rows(page, members)" in source
    assert "Raid job for this context" in source
    assert "Team/boss assignment is context" in source
