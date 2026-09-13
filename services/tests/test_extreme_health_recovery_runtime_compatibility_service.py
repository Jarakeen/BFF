from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)
from services.extreme_health_recovery_runtime_compatibility_service import (
    ExtremeHealthRecoveryCompatibility,
    ExtremeHealthRecoveryRuntimeCompatibilityService,
    ExtremeHealthRecoveryRuntimeState,
)


def _branch(name: str, description: str, pieces: int = 5):
    row = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name=name,
        piece_count=pieces,
        description=description,
        objective_key="health_recovery",
    )
    assert row is not None
    return row


def test_dominant_shared_runtime_state_is_jointly_compatible():
    state = ExtremeHealthRecoveryRuntimeState()
    assert state.dominant_shared_state_compatible is True


def test_green_pact_requires_food_instead_of_direct_drink_incumbent():
    branch = _branch(
        "Green Pact",
        "While you have a food buff active, your Health Recovery is increased by 8-356 and your Max Health by 2500.",
    )
    result = ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
        branch, ExtremeHealthRecoveryRuntimeState(provisioning_kind="drink")
    )
    assert result.status is ExtremeHealthRecoveryCompatibility.ALTERNATE_PROVISIONING


def test_major_fortitude_set_is_redundant_when_potion_buff_is_active():
    branch = _branch(
        "Apocryphal Inspiration",
        "You and group members gain Major Fortitude, Major Intellect, and Major Endurance, increasing recovery by 30%.",
    )
    result = ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
        branch, ExtremeHealthRecoveryRuntimeState(major_fortitude_active=True)
    )
    assert result.status is ExtremeHealthRecoveryCompatibility.REDUNDANT_NAMED_BUFF


def test_low_health_and_recent_ultimate_branches_can_coexist_with_dominant_state():
    state = ExtremeHealthRecoveryRuntimeState()
    orgnum = _branch(
        "Orgnum's Scales",
        "While you are below 60% Health, increase your Health Recovery by 800 and your Physical and Spell Resistance by 6400.",
    )
    soulwell = _branch(
        "Lustrous Soulwell",
        "After using an Ultimate, gain 465 Health, Magicka, and Stamina Recovery.",
    )
    assert ExtremeHealthRecoveryRuntimeCompatibilityService.assess(orgnum, state).status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
    assert ExtremeHealthRecoveryRuntimeCompatibilityService.assess(soulwell, state).status is ExtremeHealthRecoveryCompatibility.COMPATIBLE


def test_twice_born_star_remains_separate_search_state():
    branch = _branch(
        "Twice-Born Star",
        "You can have two Mundus Stone boons at the same time.",
    )
    result = ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
        branch, ExtremeHealthRecoveryRuntimeState()
    )
    assert result.status is ExtremeHealthRecoveryCompatibility.SEARCH_STATE_MUTATION
