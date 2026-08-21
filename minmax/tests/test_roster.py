from minmax.roster import (
    Role,
    RosterRequest,
    RosterSlot,
)


def test_roster_request_counts_remaining_slots():
    request = RosterRequest(
        trial="Sunspire",
        party_size=12,
        objective="max_group_damage",
        fixed_slots=[
            RosterSlot(Role.TANK, "Sorcerer", locked=True),
            RosterSlot(Role.HEALER, "Warden", locked=True),
            RosterSlot(Role.HEALER, "Arcanist", locked=True),
            RosterSlot(Role.DD, "Nightblade", locked=True),
            RosterSlot(Role.DD, "Nightblade", locked=True),
            RosterSlot(Role.DD, archetype="Werewolf", locked=True),
            RosterSlot(Role.DD, archetype="ZensKosh", locked=True),
        ],
    )

    assert request.remaining_slots == 5


def test_roster_slot_preserves_constraints():
    slot = RosterSlot(
        role=Role.DD,
        class_name="Nightblade",
        locked=True,
    )

    assert slot.role == Role.DD
    assert slot.class_name == "Nightblade"
    assert slot.locked is True