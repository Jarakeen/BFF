from minmax.candidate_requirements import CandidateRequirement
from minmax.roster import (
    Role,
    RosterCandidate,
    RosterRequest,
    RosterSlot,
)
from minmax.roster_solver import RosterSolver


def test_friends_sunspire_group_has_three_open_slots():

    request = RosterRequest(
        trial="Sunspire",
        party_size=12,
        objective="max_group_damage",

        fixed_slots=[
            RosterSlot(Role.TANK, "Sorcerer", locked=True),
            RosterSlot(Role.HEALER, "Warden", locked=True),

            RosterSlot(Role.DD, "Necromancer", locked=True),
            RosterSlot(Role.DD, "Necromancer", locked=True),
            RosterSlot(Role.DD, "Arcanist", locked=True),
            RosterSlot(Role.DD, "Templar", locked=True),
            RosterSlot(Role.DD, "Nightblade", locked=True),
            RosterSlot(Role.DD, "Nightblade", locked=True),
            RosterSlot(Role.DD, "Dragonknight / Zen", locked=True),
        ],

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

    assert request.party_size == 12
    assert len(request.fixed_slots) == 9
    assert request.remaining_slots == 3
    assert len(request.candidate_requirements) == 3


def test_friends_sunspire_solver_fills_the_three_missing_slots():

    request = RosterRequest(
        trial="Sunspire",
        party_size=12,
        objective="max_group_damage",

        fixed_slots=[
            RosterSlot(Role.TANK, "Sorcerer", locked=True),
            RosterSlot(Role.HEALER, "Warden", locked=True),

            RosterSlot(Role.DD, "Necromancer", locked=True),
            RosterSlot(Role.DD, "Necromancer", locked=True),
            RosterSlot(Role.DD, "Arcanist", locked=True),
            RosterSlot(Role.DD, "Templar", locked=True),
            RosterSlot(Role.DD, "Nightblade", locked=True),
            RosterSlot(Role.DD, "Nightblade", locked=True),
            RosterSlot(Role.DD, "Dragonknight / Zen", locked=True),
        ],

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
            name="Wrong Tank",
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
            name="Wrong Healer",
            role=Role.HEALER,
            class_name="Warden",
            personal_damage=100,
        ),
        RosterCandidate(
            name="150K DD",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=150,
        ),
        RosterCandidate(
            name="165K DD",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=165,
        ),
        RosterCandidate(
            name="180K DD",
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

    assert len(result.roster) == 3

    assert "Necro Tank" in names
    assert "Arc Healer" in names
    assert "180K DD" in names

    assert "Wrong Tank" not in names
    assert "Wrong Healer" not in names
    assert "150K DD" not in names


    def test_friends_sunspire_missing_dd_is_selected_by_group_damage():
        assert result.roster[-1].name == "Support DD"
        assert result.evaluation.group_damage > ...