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


def test_comp_maker_saved_build_candidates_are_scoped_to_loaded_player() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "def _candidate_matches_roster_member" in source
    assert 'candidate.source_kind != "saved_build"' in source
    assert 'getattr(member, "PlayerName"' in source
    assert 'getattr(member, "CharacterName"' in source
    assert "if _candidate_matches_roster_member(candidate, member, recruit=recruit)" in source


def test_comp_maker_send_preserves_known_player_without_forcing_recruitment() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert 'roster_members = getattr(self, "_comp_roster_member_by_slot", {})' in source
    assert "if not applied and not roster_members:" in source
    assert "known_player = bool(roster_context_active and roster_member is not None)" in source
    assert 'player_name=roster_player if known_player else "Recruitment Needed"' in source
    assert 'character_name=roster_character if known_player else ""' in source


def test_comp_maker_recruit_slots_do_not_borrow_saved_player_builds() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "def _row_is_recruit(page, row: int) -> bool:" in source
    assert 'if recruit and candidate.source_kind == "saved_build":' in source
    assert "return False" in source
