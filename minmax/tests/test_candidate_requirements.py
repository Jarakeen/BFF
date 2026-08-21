from minmax.candidate_requirements import CandidateRequirement
from minmax.roster import Role, RosterCandidate


def test_requirement_matches_correct_class_and_role():

    requirement = CandidateRequirement(
        role=Role.TANK,
        required_class="Necromancer",
    )

    candidate = RosterCandidate(
        name="Necro Tank",
        role=Role.TANK,
        class_name="Necromancer",
        personal_damage=50,
    )

    assert requirement.matches(candidate)


def test_requirement_rejects_wrong_class():

    requirement = CandidateRequirement(
        role=Role.TANK,
        required_class="Necromancer",
    )

    candidate = RosterCandidate(
        name="Sorc Tank",
        role=Role.TANK,
        class_name="Sorcerer",
        personal_damage=50,
    )

    assert not requirement.matches(candidate)


def test_requirement_rejects_wrong_role():

    requirement = CandidateRequirement(
        role=Role.HEALER,
        required_class="Arcanist",
    )

    candidate = RosterCandidate(
        name="Arc DD",
        role=Role.DD,
        class_name="Arcanist",
        personal_damage=180,
    )

    assert not requirement.matches(candidate)


def test_requirement_rejects_below_minimum_damage():

    requirement = CandidateRequirement(
        role=Role.DD,
        minimum_personal_damage=165,
    )

    candidate = RosterCandidate(
        name="150K Nightblade",
        role=Role.DD,
        class_name="Nightblade",
        personal_damage=150,
    )

    assert not requirement.matches(candidate)


def test_requirement_accepts_exact_minimum_damage():

    requirement = CandidateRequirement(
        role=Role.DD,
        minimum_personal_damage=165,
    )

    candidate = RosterCandidate(
        name="165K Nightblade",
        role=Role.DD,
        class_name="Nightblade",
        personal_damage=165,
    )

    assert requirement.matches(candidate)


def test_requirement_accepts_damage_above_minimum():

    requirement = CandidateRequirement(
        role=Role.DD,
        minimum_personal_damage=165,
    )

    candidate = RosterCandidate(
        name="180K Nightblade",
        role=Role.DD,
        class_name="Nightblade",
        personal_damage=180,
    )

    assert requirement.matches(candidate)