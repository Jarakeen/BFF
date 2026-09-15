from pathlib import Path

from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
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
