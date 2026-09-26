from __future__ import annotations

from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_assignment_context_service import RosterAssignmentContextService
from services.roster_service import RosterService


def _services(tmp_path):
    database = EsoDatabase(tmp_path / "roster.db")
    roster = RosterService(database)
    context = RosterAssignmentContextService(database)
    member_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Team="Disappointing Feral, Swine & Punishment",
        )
    )
    return roster, context, member_id


def test_same_member_can_have_different_team_default_jobs(tmp_path) -> None:
    roster, context, member_id = _services(tmp_path)

    context.set_field(
        member_id,
        team_name="Disappointing Feral",
        field="primary_assignment",
        value="Kite Healer",
    )
    context.set_field(
        member_id,
        team_name="Swine & Punishment",
        field="primary_assignment",
        value="Slayer Healer",
    )

    assert context.get_effective_assignment(
        member_id,
        team_name="Disappointing Feral",
        legacy_service=roster,
    )["primary_assignment"] == "Kite Healer"
    assert context.get_effective_assignment(
        member_id,
        team_name="Swine & Punishment",
        legacy_service=roster,
    )["primary_assignment"] == "Slayer Healer"


def test_boss_override_inherits_unchanged_team_fields(tmp_path) -> None:
    roster, context, member_id = _services(tmp_path)

    context.set_field(
        member_id,
        team_name="Swine & Punishment",
        field="primary_assignment",
        value="Slayer Healer",
    )
    context.set_field(
        member_id,
        team_name="Swine & Punishment",
        field="secondary_assignment",
        value="Orbs / Utility",
    )
    context.set_field(
        member_id,
        team_name="Swine & Punishment",
        encounter_id="boss_a",
        field="primary_assignment",
        value="Kite Healer",
    )

    resolved = context.get_effective_assignment(
        member_id,
        team_name="Swine & Punishment",
        encounter_id="boss_a",
        legacy_service=roster,
    )

    assert resolved["primary_assignment"] == "Kite Healer"
    assert resolved["secondary_assignment"] == "Orbs / Utility"
    assert resolved["_encounter_fields"] == ("primary_assignment",)


def test_other_bosses_keep_team_default(tmp_path) -> None:
    roster, context, member_id = _services(tmp_path)

    context.set_field(
        member_id,
        team_name="Swine & Punishment",
        field="primary_assignment",
        value="Slayer Healer",
    )
    context.set_field(
        member_id,
        team_name="Swine & Punishment",
        encounter_id="boss_a",
        field="primary_assignment",
        value="Portal Healer",
    )

    assert context.get_effective_assignment(
        member_id,
        team_name="Swine & Punishment",
        encounter_id="boss_b",
        legacy_service=roster,
    )["primary_assignment"] == "Slayer Healer"


def test_legacy_assignment_remains_fallback_until_team_default_is_saved(tmp_path) -> None:
    roster, context, member_id = _services(tmp_path)
    roster.set_member_assignment_field(member_id, "notes", "Old roster note")

    resolved = context.get_effective_assignment(
        member_id,
        team_name="Swine & Punishment",
        encounter_id="boss_a",
        legacy_service=roster,
    )

    assert resolved["notes"] == "Old roster note"
    assert resolved["_source"] == "legacy"


def test_assignment_context_rejects_oversized_value_before_mutation(tmp_path) -> None:
    roster, context, member_id = _services(tmp_path)
    team = "Swine & Punishment"

    context.set_field(
        member_id,
        team_name=team,
        field="notes",
        value="Keep this",
    )

    try:
        context.set_field(
            member_id,
            team_name=team,
            field="notes",
            value="x" * 12001,
        )
    except ValueError as exc:
        assert "Pydantic validation" in str(exc)
    else:
        raise AssertionError("oversized assignment context was accepted")

    resolved = context.get_effective_assignment(
        member_id,
        team_name=team,
        legacy_service=roster,
    )
    assert resolved["notes"] == "Keep this"


def test_assignment_context_rejects_invalid_team_before_creation(tmp_path) -> None:
    roster, context, member_id = _services(tmp_path)
    before = tuple(roster.list_team_names())

    try:
        context.set_field(
            member_id,
            team_name="x" * 241,
            field="gear_needed",
            value="PA ice staff",
        )
    except ValueError as exc:
        assert "Pydantic validation" in str(exc)
    else:
        raise AssertionError("invalid team identity was accepted")

    assert tuple(roster.list_team_names()) == before
