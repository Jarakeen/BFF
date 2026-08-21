from minmax.roster import (
    Role,
    RosterCandidate,
    RosterRequest,
)
from minmax.roster_solver import RosterSolver
from minmax.candidate_requirements import CandidateRequirement


def test_solver_fills_specific_candidate_requirements():

    request = RosterRequest(
        trial="Sunspire",
        party_size=3,
        objective="max_group_damage",
        fixed_slots=[],
        candidate_requirements=[
            CandidateRequirement(
                role=Role.TANK,
                required_class="Necromancer",
            ),
            CandidateRequirement(
                role=Role.HEALER,
                required_class="Arcanist",
            ),
            CandidateRequirement(
                role=Role.DD,
                minimum_personal_damage=165,
            ),
        ],
    )

    candidates = [
        RosterCandidate(
            name="Necro Tank",
            role=Role.TANK,
            class_name="Necromancer",
            personal_damage=50,
        ),
        RosterCandidate(
            name="Sorc Tank",
            role=Role.TANK,
            class_name="Sorcerer",
            personal_damage=100,
        ),
        RosterCandidate(
            name="Arc Healer",
            role=Role.HEALER,
            class_name="Arcanist",
            personal_damage=80,
        ),
        RosterCandidate(
            name="Warden Healer",
            role=Role.HEALER,
            class_name="Warden",
            personal_damage=90,
        ),
        RosterCandidate(
            name="150K Nightblade",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=150,
        ),
        RosterCandidate(
            name="165K Nightblade",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=165,
        ),
        RosterCandidate(
            name="180K Arcanist",
            role=Role.DD,
            class_name="Arcanist",
            personal_damage=180,
        ),
    ]

    result = RosterSolver().solve(
        request=request,
        candidates=candidates,
    )

    names = {candidate.name for candidate in result.roster}

    assert "Necro Tank" in names
    assert "Arc Healer" in names
    assert "180K Arcanist" in names

    assert "Sorc Tank" not in names
    assert "Warden Healer" not in names
    assert "150K Nightblade" not in names
    