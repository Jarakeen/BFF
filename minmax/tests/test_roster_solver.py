from minmax.roster import (
    Role,
    RosterCandidate,
    RosterRequest,
    RosterSlot,
)
from minmax.roster_solver import RosterSolver


def test_solver_fills_remaining_slots_with_highest_damage_dds():

    request = RosterRequest(
        trial="Sunspire",
        party_size=5,
        objective="max_group_damage",
        fixed_slots=[
            RosterSlot(Role.TANK, "Sorcerer", locked=True),
            RosterSlot(Role.HEALER, "Warden", locked=True),
        ],
    )

    candidates = [
        RosterCandidate(
            name="Nightblade A",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=170,
        ),
        RosterCandidate(
            name="Nightblade B",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=160,
        ),
        RosterCandidate(
            name="Werewolf",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=160,
        ),
        RosterCandidate(
            name="DD 4",
            role=Role.DD,
            class_name="Necromancer",
            personal_damage=165,
        ),
        RosterCandidate(
            name="DD 5",
            role=Role.DD,
            class_name="Arcanist",
            personal_damage=150,
        ),
        RosterCandidate(
            name="Support 6",
            role=Role.DD,
            class_name="Dragonknight",
            personal_damage=145,
        ),
        RosterCandidate(
            name="DD 7",
            role=Role.DD,
            class_name="Templar",
            personal_damage=165,
        ),
        RosterCandidate(
            name="DD 8",
            role=Role.DD,
            class_name="Necromancer",
            personal_damage=165,
        ),
        RosterCandidate(
            name="Tank 2",
            role=Role.TANK,
            class_name="Necromancer",
            personal_damage=50,
        ),
        RosterCandidate(
            name="Healer 2",
            role=Role.HEALER,
            class_name="Arcanist",
            personal_damage=40,
        ),

    ]

    result = RosterSolver().solve(
        request=request,
        candidates=candidates,
    )

    assert len(result.roster) == 3

    assert result.roster[0].name == "Nightblade A"
    assert result.roster[1].name == "DD 4"
    assert result.roster[2].name == "DD 7"

    assert result.evaluation.group_damage == 500

def test_solver_can_prefer_group_support_over_personal_damage():

    request = RosterRequest(
        trial="Sunspire",
        party_size=2,
        objective="max_group_damage",
        fixed_slots=[],
    )

    candidates = [
        RosterCandidate(
            name="Pure DD",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=160,
            support_value=0,
        ),
        RosterCandidate(
            name="Support DD",
            role=Role.DD,
            class_name="Dragonknight",
            personal_damage=140,
            support_value=50,
        ),
    ]

    result = RosterSolver().solve(
        request=request,
        candidates=candidates,
    )

    assert result.roster[0].name == "Pure DD"    