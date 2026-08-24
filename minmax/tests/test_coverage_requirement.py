from minmax.coverage_requirement import CoverageRequirement
from minmax.role import Role
from minmax.support_target_type import SupportTargetType


def test_requirement_can_describe_basic_effect():
    requirement = CoverageRequirement(
        effect_name="major_slayer",
        target_type=SupportTargetType.GROUP,
        minimum_targets=5,
        maximum_range=28,
    )

    assert requirement.effect_name == "major_slayer"
    assert requirement.target_type == SupportTargetType.GROUP
    assert requirement.minimum_targets == 5
    assert requirement.maximum_range == 28


def test_requirement_preserves_uptime_and_condition():
    requirement = CoverageRequirement(
        effect_name="major_force",
        minimum_uptime=0.80,
        condition="ultimate_window",
    )

    assert requirement.minimum_uptime == 0.80
    assert requirement.condition == "ultimate_window"


def test_requirement_preserves_role_constraints():
    requirement = CoverageRequirement(
        effect_name="major_courage",
        required_roles=frozenset({Role.HEALER, Role.TANK}),
        priority=10,
    )

    assert requirement.required_roles == frozenset(
        {Role.HEALER, Role.TANK}
    )
    assert requirement.priority == 10


def test_invalid_requirement_values_are_rejected():
    try:
        CoverageRequirement(
            effect_name="major_slayer",
            minimum_uptime=1.5,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid uptime to raise ValueError")

def test_major_courage_requires_one_provider():
    requirement = CoverageRequirement(
        effect_name="major_courage",
    )

    assert requirement.required_provider_count == 1
