from minmax.role import Role
from minmax.roster import (
    RosterCandidate,
    RosterRequest,
    RosterSlot,
)
from minmax.roster_constraints import RoleRequirement


def test_role_requirement_preserves_role_and_count():
    requirement = RoleRequirement(
        role=Role.TANK,
        count=2,
    )

    assert requirement.role == Role.TANK
    assert requirement.count == 2


def test_fixed_slots_count_toward_role_requirement():

    request = RosterRequest(
        trial="Sunspire",
        party_size=12,
        objective="max_group_damage",
        fixed_slots=[
            RosterSlot(
                role=Role.TANK,
                class_name="Sorcerer",
                locked=True,
            ),
            RosterSlot(
                role=Role.HEALER,
                class_name="Warden",
                locked=True,
            ),
        ],
        role_requirements=(
            RoleRequirement(Role.TANK, 2),
            RoleRequirement(Role.HEALER, 2),
            RoleRequirement(Role.DD, 8),
        ),
    )

    assert request.remaining_slots == 10

def test_solver_fills_missing_roles_before_extra_dps():

    request = RosterRequest(
        trial="Sunspire",
        party_size=4,
        objective="max_group_damage",
        fixed_slots=[],
        role_requirements=(
            RoleRequirement(Role.TANK, 1),
            RoleRequirement(Role.HEALER, 1),
            RoleRequirement(Role.DD, 2),
        ),
    )

    candidates = [
        RosterCandidate(
            name="Huge DPS",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=200,
        ),
        RosterCandidate(
            name="Another Huge DPS",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=190,
        ),
        RosterCandidate(
            name="Tank",
            role=Role.TANK,
            class_name="Dragonknight",
            personal_damage=50,
        ),
        RosterCandidate(
            name="Healer",
            role=Role.HEALER,
            class_name="Warden",
            personal_damage=40,
        ),
    ]

    from minmax.roster_solver import RosterSolver

    result = RosterSolver().solve(
        request=request,
        candidates=candidates,
    )

    roles = [candidate.role for candidate in result.roster]

    assert roles.count(Role.TANK) == 1
    assert roles.count(Role.HEALER) == 1
    assert roles.count(Role.DD) == 2

def test_solver_rejects_impossible_role_requirements():

    request = RosterRequest(
        trial="Sunspire",
        party_size=4,
        objective="max_group_damage",
        fixed_slots=[],
        role_requirements=(
            RoleRequirement(Role.TANK, 2),
            RoleRequirement(Role.HEALER, 2),
        ),
    )

    candidates = [
        RosterCandidate(
            name="Only Tank",
            role=Role.TANK,
            class_name="Sorcerer",
        ),
    ]

    from minmax.roster_solver import RosterSolver

    try:
        RosterSolver().solve(
            request=request,
            candidates=candidates,
        )
    except ValueError as error:
        assert "tank" in str(error).lower()
    else:
        raise AssertionError(
            "Expected impossible roster to raise ValueError"
        )