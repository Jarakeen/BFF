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
    assert "Team/boss assignment remains context" in source


def test_comp_maker_saved_build_candidates_are_scoped_to_loaded_player() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "def _candidate_matches_roster_member" in source
    assert 'candidate.source_kind != "saved_build"' in source
    assert 'getattr(member, "PlayerName"' in source
    assert 'getattr(member, "CharacterName"' in source
    assert "if _candidate_matches_roster_member(candidate, member, recruit=recruit)" in source


def test_comp_maker_roster_intake_preserves_known_player_in_canonical_state() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    sync = source.split("def _sync_comp_state_from_matches", 1)[1].split(
        "def apply_roster_team_context", 1
    )[0]
    assert 'player = str(getattr(member, "PlayerName", "") or "").strip()' in sync
    assert "recruit = _is_recruit_member(member)" in sync
    assert 'changes["player_name"] = "" if recruit else player' in sync
    assert 'changes["character_name"] = character' in sync
    assert "page._comp_plan_state = current" in sync


def test_comp_maker_recruit_slots_do_not_borrow_saved_player_builds() -> None:
    source = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "def _row_is_recruit(page, row: int) -> bool:" in source
    assert 'if recruit and candidate.source_kind == "saved_build":' in source
    assert "return False" in source


def test_roster_intake_creates_canonical_comp_state_before_raid_plan_exists() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    ensure = source.split("def _ensure_unbound_comp_state", 1)[1].split(
        "def _load_roster_shape", 1
    )[0]
    apply = source.split("def apply_roster_team_context", 1)[1].split(
        "def _send_roster_team_to_comp", 1
    )[0]
    sync = source.split("def _sync_comp_state_from_matches", 1)[1].split(
        "def apply_roster_team_context", 1
    )[0]

    assert "existing.is_raid_plan_bound" in ensure
    assert "CompPlanStateService.new_unbound(" in ensure
    assert "raid_plan_name=name" in ensure
    assert "team_name=str(team_name" in ensure
    assert "_ensure_unbound_comp_state(" in apply
    assert "_sync_comp_state_from_matches(page, matched, assignments)" in apply
    assert 'changes["primary_assignment"] = primary' in sync
    assert 'changes["secondary_assignment"] = secondary' in sync


def test_comp_roster_intake_renders_only_after_lock_aware_state_sync() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")
    apply = source.split("def apply_roster_team_context", 1)[1].split(
        "def _send_roster_team_to_comp", 1
    )[0]

    assert apply.index("_sync_comp_state_from_matches(page, matched, assignments)") < apply.index(
        "_set_player(page, row, member, assignments.get(member_id))"
    )
    setter = source.split("def _set_player", 1)[1].split("def _clear_player_rows", 1)[0]
    assert "Canonical Comp state accepted this roster context." in setter
