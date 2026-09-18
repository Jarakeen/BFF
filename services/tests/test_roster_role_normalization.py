from models.roster_model import ROLES, RosterMember, normalize_roster_role


def test_roster_exposes_one_standard_damage_role_plus_support_dd() -> None:
    assert ROLES == ["", "Tank", "Healer", "DD", "Support DD"]
    assert "Damage Dealer" not in ROLES


def test_legacy_damage_role_spellings_normalize_to_dd() -> None:
    for value in ("DD", "DPS", "Damage", "Damage Dealer", "damage_dealer"):
        assert normalize_roster_role(value) == "DD"


def test_support_dd_remains_distinct() -> None:
    for value in ("Support DD", "Support DPS", "support_damage_dealer"):
        assert normalize_roster_role(value) == "Support DD"

    member = RosterMember(
        PlayerName="Test",
        PrimaryRole="Damage Dealer",
        SecondaryRole="Support DD",
    )
    assert member.PrimaryRole == "DD"
    assert member.SecondaryRole == "Support DD"
