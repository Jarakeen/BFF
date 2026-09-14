from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterResponsibilityBindingService,
)


def test_xalvakka_binds_reviewed_main_off_tank_slots_to_distinct_lanes():
    result = RaidTankEncounterResponsibilityBindingService().bind(
        encounter_id="xalvakka",
        prescription_slot_members={
            "Main Tank": "tank-a",
            "Off Tank": "tank-b",
            "Healer 1": "healer-a",
        },
        member_capabilities={
            "tank-a": ("taunt",),
            "tank-b": ("taunt",),
            "healer-a": (),
        },
    )

    assert result.resolved is True
    assert [(row.lane_id, row.member_id) for row in result.assignments] == [
        ("boss_holder", "tank-a"),
        ("add_handler", "tank-b"),
    ]
    assert [
        row.responsibility.responsibility_id for row in result.for_member("tank-b")
    ] == [
        "pack_encounter_adds",
        "iron_atronach_opening_position",
        "daedroth_facing",
    ]


def test_xalvakka_binding_fails_closed_when_off_tank_slot_is_missing():
    result = RaidTankEncounterResponsibilityBindingService().bind(
        encounter_id="xalvakka",
        prescription_slot_members={"Main Tank": "tank-a"},
        member_capabilities={"tank-a": ("taunt",)},
    )

    assert result.resolved is False
    assert "add_handler" in result.unresolved[0]
    assert "exactly one authoritative prescription slot" in result.unresolved[0]


def test_xalvakka_binding_rejects_same_member_in_distinct_tank_slots():
    result = RaidTankEncounterResponsibilityBindingService().bind(
        encounter_id="xalvakka",
        prescription_slot_members={
            "Main Tank": "tank-a",
            "Off Tank": "tank-a",
        },
        member_capabilities={"tank-a": ("taunt",)},
    )

    assert result.resolved is False
    assert any("cannot both be assigned" in row for row in result.unresolved)


def test_xalvakka_binding_requires_canonical_taunt_for_add_handler():
    result = RaidTankEncounterResponsibilityBindingService().bind(
        encounter_id="xalvakka",
        prescription_slot_members={
            "Main Tank": "tank-a",
            "Off Tank": "tank-b",
        },
        member_capabilities={
            "tank-a": ("taunt",),
            "tank-b": (),
        },
    )

    assert result.resolved is False
    assert any("lacks required canonical capability evidence: taunt" in row for row in result.unresolved)


def test_encounter_without_reviewed_lanes_is_noop():
    result = RaidTankEncounterResponsibilityBindingService().bind(
        encounter_id="taleria_hm",
        prescription_slot_members={"Main Tank": "tank-a"},
        member_capabilities={"tank-a": ("taunt",)},
    )

    assert result.resolved is True
    assert result.assignments == ()
    assert result.responsibilities == ()
