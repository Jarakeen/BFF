from pathlib import Path

from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from services.raid_plan_repository import RaidPlanRepository
from ui import raid_plan_persistence_page
from ui.raid_plan_persistence_page import merge_visible_plan_with_loaded_snapshot


def test_save_merge_preserves_hidden_assignment_and_triggered_state() -> None:
    loaded = RaidPlan(
        plan_id="rockgrove-plan",
        trial_id="rockgrove",
        name="Rockgrove Plan",
        team_name="Performance Mode",
        status="active",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                roster_member_id=7,
                player_id="player-id",
                character_id="magrat-id",
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_id="df-healer-id",
                selected_build_name="DF Healer",
                primary_assignment="Group Healer",
                secondary_assignment="Portal Backup",
                notes="Top-left pool",
            ),
        ),
        triggered_responsibilities=(
            RaidPlanTriggeredResponsibility(
                responsibility_id="portal-response",
                seat_id="healer-1",
                encounter_id="xalvakka-hm",
                trigger_key="portal_active",
                directive="Cover portal group",
            ),
        ),
    )
    visible = RaidPlan(
        plan_id="rockgrove-plan",
        trial_id="rockgrove",
        name="Rockgrove Plan Revised",
        difficulty="Veteran Hardmode",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                player_id="player-id",
                character_id="magrat-id",
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_id="rojo-healer-id",
                selected_build_name="ROJO Healer",
            ),
        ),
    )

    merged = merge_visible_plan_with_loaded_snapshot(visible, loaded)

    member = merged.member("healer-1")
    assert member is not None
    assert member.selected_build_id == "rojo-healer-id"
    assert member.selected_build_name == "ROJO Healer"
    assert member.roster_member_id == 7
    assert member.player_id == "player-id"
    assert member.character_id == "magrat-id"
    assert member.primary_assignment == "Group Healer"
    assert member.secondary_assignment == "Portal Backup"
    assert member.notes == "Top-left pool"
    assert merged.team_name == "Performance Mode"
    assert merged.status == "active"
    assert merged.triggered_responsibilities == loaded.triggered_responsibilities


def test_persistence_page_resolves_selected_build_into_stable_member_identity() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert "RaidPlanMemberIdentityResolutionService" in source
    assert "selected_build_id=selected_ids.get(member.seat_id.casefold())" in source
    assert "resolver.resolve(candidate)" in source
    assert "roster_member_id=resolution.roster_member_id" in source
    assert "player_id=resolution.player_id" in source
    assert "character_id=resolution.character_id" in source
    assert 'build_id = _clean(getattr(self.saved_builds[saved_index], "BuildId", ""))' in source
    assert "if member.selected_build_id:" in source
    assert "if not matched and member.selected_build_name:" in source


def test_hidden_character_identity_is_not_carried_to_changed_character() -> None:
    loaded = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                roster_member_id=7,
                player_id="player-id",
                character_id="magrat-id",
                character_name="Magrat",
            ),
        ),
    )
    visible = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                player_id="player-id",
                character_name="Other Toon",
            ),
        ),
    )

    merged = merge_visible_plan_with_loaded_snapshot(visible, loaded)
    member = merged.member("healer-1")

    assert member is not None
    assert member.player_id == "player-id"
    assert member.character_id is None
    assert member.roster_member_id is None


def test_matching_gamertag_does_not_override_conflicting_stable_player_identity() -> None:
    loaded = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Same Display",
                player_id="player-a",
                notes="Player A note",
            ),
        ),
    )
    visible = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Same Display",
                player_id="player-b",
            ),
        ),
    )

    merged = merge_visible_plan_with_loaded_snapshot(visible, loaded)

    member = merged.member("dd-1")
    assert member is not None
    assert member.player_id == "player-b"
    assert member.notes is None


def test_matching_character_name_does_not_override_conflicting_stable_character_identity() -> None:
    loaded = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Jarakeen",
                player_id="player-id",
                character_id="character-a",
                character_name="Same Name",
                roster_member_id=7,
            ),
        ),
    )
    visible = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Jarakeen",
                player_id="player-id",
                character_id="character-b",
                character_name="Same Name",
            ),
        ),
    )

    merged = merge_visible_plan_with_loaded_snapshot(visible, loaded)

    member = merged.member("dd-1")
    assert member is not None
    assert member.character_id == "character-b"
    assert member.roster_member_id is None


def test_hidden_member_state_is_not_carried_to_a_different_player() -> None:
    loaded = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Original",
                primary_assignment="Portal DD",
            ),
        ),
    )
    visible = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(RaidPlanMember(seat_id="dd-1", gamertag="Replacement"),),
    )

    merged = merge_visible_plan_with_loaded_snapshot(visible, loaded)

    assert merged.member("dd-1").primary_assignment is None


def test_legacy_rows_still_merge_by_gamertag_when_no_stable_player_id_exists() -> None:
    loaded = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Legacy Friend",
                character_name="Legacy Toon",
                notes="Legacy note",
            ),
        ),
    )
    visible = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="legacy friend",
                character_name="legacy toon",
            ),
        ),
    )

    merged = merge_visible_plan_with_loaded_snapshot(visible, loaded)

    assert merged.member("dd-1").notes == "Legacy note"


def test_hidden_state_is_not_carried_across_trial_change() -> None:
    loaded = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(RaidPlanMember(seat_id="dd-1", gamertag="Friend", notes="RG only"),),
    )
    visible = RaidPlan(
        plan_id="new-plan",
        trial_id="dreadsail-reef",
        name="New Plan",
        members=(RaidPlanMember(seat_id="dd-1", gamertag="Friend"),),
    )

    assert merge_visible_plan_with_loaded_snapshot(visible, loaded) == visible


def test_repository_round_trip_preserves_character_role_and_planned_build(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    plan = RaidPlan(
        plan_id="sunspire-gs",
        trial_id="sunspire",
        name="GS",
        difficulty="Veteran Hardmode",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_name="DF Healer",
                planned_gear_sets=("Spell Power Cure", "Pillager's Profit"),
                planned_mundus="The Ritual",
            ),
        ),
    )

    repository.save(plan)
    loaded = repository.get(plan.plan_id)

    assert loaded == plan
    assert loaded.member("healer-1").character_name == "Magrat"
    assert loaded.member("healer-1").role == "Healer"
    assert loaded.member("healer-1").planned_gear_sets == (
        "Spell Power Cure",
        "Pillager's Profit",
    )


def test_save_current_plan_verifies_repository_round_trip() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert "persisted = self.plan_repository.get(plan.plan_id)" in source
    assert "saved Raid Plan did not round-trip exactly" in source
    assert "character(s)" in source
    assert "role(s)" in source


def test_save_merge_keeps_new_visible_class_instead_of_old_blank_snapshot() -> None:
    loaded = RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="RG",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Recruit",
                role="Healer",
                eso_class=None,
            ),
        ),
    )
    visible = RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="RG",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Recruit",
                role="Healer",
                eso_class="Warden",
            ),
        ),
    )

    merged = merge_visible_plan_with_loaded_snapshot(visible, loaded)

    assert merged.member("healer-1").eso_class == "Warden"


def test_raid_plan_save_links_named_players_to_loaded_plan_team() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert "def _active_team_name(self)" in source
    assert "self.roster_service.add_member_to_team(member_id, team_name)" in source
    assert "def save_player_to_personnel(self, row: int)" in source


def test_loaded_comp_plan_surfaces_planned_sets_in_build_picker() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert '" + ".join(member.planned_gear_sets[:2])' in source
    assert 'f"Planned • {planned_sets}"' in source
    assert "Qt.ItemDataRole.ToolTipRole" in source


def test_save_captures_visible_chair_state_before_personnel_refresh() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert "visible_before_sync = super().current_plan()" in source
    assert source.index("visible_before_sync = super().current_plan()") < source.index(
        "created_players = self._ensure_named_players_in_personnel()"
    )
    ensure_body = source.split("def _ensure_named_players_in_personnel", 1)[1].split(
        "def save_player_to_personnel", 1
    )[0]
    assert "self.refresh_personnel()" not in ensure_body
    assert "self.refresh_personnel()" in source
    assert "self.apply_plan(persisted)" in source


def test_save_restores_captured_visible_player_character_class_and_build_name() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert "gamertag=captured_by_seat.get(" in source
    assert "character_name=captured_by_seat.get(" in source
    assert "role=captured_by_seat.get(" in source
    assert "eso_class=captured_by_seat.get(" in source
    assert "selected_build_name=captured_by_seat.get(" in source

def test_raid_plan_persistence_helper_binding_contract() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert "def _refresh_action_availability(self) -> None:" in source
    assert "@staticmethod\n    def _refresh_action_availability(self)" not in source
    assert "@staticmethod\n    def _trial_display_for(plan: RaidPlan) -> str:" in source



def test_roles_surface_displays_comp_planning_package_without_selected_build_name() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "member.planned_gear_sets" in source
    assert 'or member.build_source_name' in source
    assert 'or "Comp Maker package"' in source
    assert 'f"Planned • {planned_sets}"' in source


def test_stale_selected_build_id_is_repaired_before_current_plan_validation() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "def _repair_loaded_snapshot_after_missing_builds" in source
    assert "build_id in build_ids" in source
    assert "selected_build_id=replacement_id or None" in source
    assert source.index("self._repair_loaded_snapshot_after_missing_builds(catalog)") < source.index(
        "visible = super().current_plan()"
    )


def test_stale_build_repair_preserves_planned_state_and_assignments() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")
    repair = source.split("def _repair_loaded_snapshot_after_missing_builds", 1)[1].split(
        "def _repair_loaded_snapshot_after_player_merges", 1
    )[0]

    assert "member.with_selection(" in repair
    assert "selected_build_id=replacement_id or None" in repair
    assert "planned_gear_sets=" not in repair
    assert "planned_skills=" not in repair
    assert "primary_assignment=" not in repair


def test_roles_exact_build_id_can_bypass_display_identity_filters() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")
    assert "Exact canonical BuildId outranks display-name filters." in source
    assert "exact_saved_index = next(" in source
    assert "build_combo.addItem(" in source


def test_planning_pages_reload_latest_saved_plan_on_entry() -> None:
    source = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")
    assert "def showEvent(self, event) -> None:" in source
    assert "latest = self.plan_repository.get(loaded.plan_id)" in source
    assert "self.apply_plan(latest)" in source
