from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService


def test_archive_hides_member_but_preserves_notes_and_restore(tmp_path):
    db_path = tmp_path / "eso.db"
    service = RosterService(EsoDatabase(db_path))
    member_id = service.create_member(
        RosterMember(
            PlayerName="CurrentTag",
            Team="Performance Mode",
            PersonnelNotes="Former core healer. Left on good terms.",
        )
    )

    archived = service.archive_member(member_id)

    assert archived.Status == "Archived"
    assert service.list_members() == []

    all_members = service.list_members(include_archived=True)
    assert len(all_members) == 1
    assert all_members[0].PersonnelNotes == "Former core healer. Left on good terms."
    assert all_members[0].Team == "Performance Mode"

    restored = service.restore_member(member_id)
    assert restored.Status == "Active"
    assert [member.PlayerName for member in service.list_members()] == ["CurrentTag"]


def test_permanent_delete_requires_archive_first(tmp_path):
    db_path = tmp_path / "eso.db"
    service = RosterService(EsoDatabase(db_path))
    member_id = service.create_member(RosterMember(PlayerName="KeepMe"))

    try:
        service.delete_member(member_id)
    except ValueError as exc:
        assert "archived" in str(exc).casefold()
    else:
        raise AssertionError("active Personnel record was permanently deleted")

    assert service.get_member(member_id) is not None

    service.archive_member(member_id)
    service.delete_member(member_id)
    assert service.get_member(member_id) is None


def test_former_gamertags_are_durable_exact_aliases(tmp_path):
    db_path = tmp_path / "eso.db"
    database = EsoDatabase(db_path)
    roster = RosterService(database)
    member_id = roster.create_member(
        RosterMember(
            PlayerName="NewTag",
            PersonnelNotes="Previously raided under OldTag.",
        )
    )
    identities = RosterPlayerIdentityService(database)

    assert identities.add_alias(member_id, "OldTag", source="former_gamertag") is True

    aliases = identities.aliases_for_member(member_id)
    assert [alias.alias for alias in aliases] == ["OldTag"]
    assert [member.Id for member in identities.matching_members("OldTag")] == [member_id]

    roster.archive_member(member_id)

    # Archived Personnel are intentionally excluded from active identity matching.
    assert identities.matching_members("OldTag") == []
    archived = roster.get_member(member_id)
    assert archived is not None
    assert archived.PersonnelNotes == "Previously raided under OldTag."
    assert [alias.alias for alias in identities.aliases_for_member(member_id)] == ["OldTag"]
