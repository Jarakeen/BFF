from minmax.coverage_gap import (
    CoverageGapAnalyzer,
    CoverageStatus,
)
from minmax.coverage_requirement import CoverageRequirement
from minmax.role import Role
from minmax.roster_capability_resolver import RosterCapabilityProvider
from minmax.roster_coverage import RosterCoverageAnalyzer
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def _effect(
    name: str,
    *,
    target_type: SupportTargetType = SupportTargetType.GROUP,
    target_count: int | None = None,
    range: float | None = None,
    roles: frozenset[Role] = frozenset(),
) -> SupportEffect:
    return SupportEffect(
        source="Test Source",
        name=name,
        category=SupportEffectCategory.BUFF,
        effect_type=name,
        target_type=target_type,
        target_count=target_count,
        range=range,
        role_relevance=roles,
    )


def _provider(
    name: str,
    effect: SupportEffect,
) -> RosterCapabilityProvider:
    return RosterCapabilityProvider(
        character_name=name,
        role=Role.HEALER,
        effect=effect,
    )


def _coverage(
    *providers: RosterCapabilityProvider,
    effect_name: str,
):
    return RosterCoverageAnalyzer().analyze(
        {
            effect_name: tuple(providers),
        }
    )


def test_missing_capability_is_missing():
    coverage = RosterCoverageAnalyzer().analyze({})

    requirements = (
        CoverageRequirement(effect_name="major_slayer"),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    result = analysis.for_effect("major_slayer")

    assert result is not None
    assert result.status == CoverageStatus.MISSING
    assert result.providers == ()
    assert result.satisfying_providers == ()


def test_matching_target_count_and_range_are_covered():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect(
                "major_slayer",
                target_type=SupportTargetType.GROUP,
                target_count=5,
                range=28,
            ),
        ),
        effect_name="major_slayer",
    )

    requirements = (
        CoverageRequirement(
            effect_name="major_slayer",
            target_type=SupportTargetType.GROUP,
            minimum_targets=5,
            maximum_range=28,
        ),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    result = analysis.for_effect("major_slayer")

    assert result is not None
    assert result.status == CoverageStatus.COVERED
    assert result.providers == ("Healer One",)
    assert result.satisfying_providers == ("Healer One",)


def test_insufficient_target_count_is_detected():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect(
                "major_slayer",
                target_type=SupportTargetType.GROUP,
                target_count=5,
                range=28,
            ),
        ),
        effect_name="major_slayer",
    )

    requirements = (
        CoverageRequirement(
            effect_name="major_slayer",
            target_type=SupportTargetType.GROUP,
            minimum_targets=12,
        ),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    result = analysis.for_effect("major_slayer")

    assert result is not None
    assert result.status == CoverageStatus.INSUFFICIENT
    assert result.providers == ("Healer One",)
    assert result.satisfying_providers == ()


def test_insufficient_range_is_detected():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect(
                "major_slayer",
                target_type=SupportTargetType.GROUP,
                target_count=12,
                range=10,
            ),
        ),
        effect_name="major_slayer",
    )

    requirements = (
        CoverageRequirement(
            effect_name="major_slayer",
            target_type=SupportTargetType.GROUP,
            minimum_targets=5,
            maximum_range=28,
        ),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    result = analysis.for_effect("major_slayer")

    assert result is not None
    assert result.status == CoverageStatus.INSUFFICIENT


def test_wrong_target_type_is_detected():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect(
                "major_courage",
                target_type=SupportTargetType.SELF,
            ),
        ),
        effect_name="major_courage",
    )

    requirements = (
        CoverageRequirement(
            effect_name="major_courage",
            target_type=SupportTargetType.GROUP,
        ),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    result = analysis.for_effect("major_courage")

    assert result is not None
    assert result.status == CoverageStatus.INSUFFICIENT


def test_required_role_is_checked():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect(
                "major_courage",
                roles=frozenset({Role.HEALER}),
            ),
        ),
        effect_name="major_courage",
    )

    requirements = (
        CoverageRequirement(
            effect_name="major_courage",
            required_roles=frozenset({Role.TANK}),
        ),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    result = analysis.for_effect("major_courage")

    assert result is not None
    assert result.status == CoverageStatus.INSUFFICIENT


def test_multiple_providers_keep_only_satisfying_providers():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect(
                "major_slayer",
                target_type=SupportTargetType.GROUP,
                target_count=5,
                range=28,
            ),
        ),
        _provider(
            "Healer Two",
            _effect(
                "major_slayer",
                target_type=SupportTargetType.GROUP,
                target_count=12,
                range=28,
            ),
        ),
        effect_name="major_slayer",
    )

    requirements = (
        CoverageRequirement(
            effect_name="major_slayer",
            target_type=SupportTargetType.GROUP,
            minimum_targets=10,
            maximum_range=28,
        ),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    result = analysis.for_effect("major_slayer")

    assert result is not None
    assert result.status == CoverageStatus.COVERED
    assert result.providers == (
        "Healer One",
        "Healer Two",
    )
    assert result.satisfying_providers == (
        "Healer Two",
    )


def test_analysis_groups_results_by_status():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect(
                "major_courage",
                target_type=SupportTargetType.GROUP,
            ),
        ),
        effect_name="major_courage",
    )

    requirements = (
        CoverageRequirement(effect_name="major_courage"),
        CoverageRequirement(effect_name="major_slayer"),
        CoverageRequirement(
            effect_name="minor_brittle",
            target_type=SupportTargetType.GROUP,
        ),
    )

    analysis = CoverageGapAnalyzer().analyze(coverage, requirements)

    assert len(analysis.covered) == 1
    assert len(analysis.missing) == 2
    assert len(analysis.insufficient) == 0
    
def test_multiple_major_courage_providers_are_redundant_not_missing():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect("major_courage"),
        ),
        _provider(
            "Healer Two",
            _effect("major_courage"),
        ),
        effect_name="major_courage",
    )

    analysis = CoverageGapAnalyzer().analyze(
        coverage,
        (
            CoverageRequirement(
                effect_name="major_courage",
                required_provider_count=1,
            ),
        ),
    )

    result = analysis.for_effect("major_courage")

    assert result is not None
    assert result.is_satisfied
    assert result.valid_provider_count == 2
    assert result.required_provider_count == 1
    assert result.redundant_provider_count == 1


def test_two_required_providers_need_two_valid_providers():
    coverage = _coverage(
        _provider(
            "Healer One",
            _effect("major_courage"),
        ),
        effect_name="major_courage",
    )

    analysis = CoverageGapAnalyzer().analyze(
        coverage,
        (
            CoverageRequirement(
                effect_name="major_courage",
                required_provider_count=2,
            ),
        ),
    )

    result = analysis.for_effect("major_courage")

    assert result is not None
    assert not result.is_satisfied
    assert result.status == CoverageStatus.INSUFFICIENT
    assert result.valid_provider_count == 1
    assert result.redundant_provider_count == 0


def test_major_and_minor_courage_are_independent_capabilities():
    coverage = RosterCoverageAnalyzer().analyze(
        {
            "major_courage": (
                _provider(
                    "Healer One",
                    _effect("major_courage"),
                ),
            ),
            "minor_courage": (
                _provider(
                    "Healer Two",
                    _effect("minor_courage"),
                ),
            ),
        }
    )

    analysis = CoverageGapAnalyzer().analyze(
        coverage,
        (
            CoverageRequirement(
                effect_name="major_courage",
            ),
            CoverageRequirement(
                effect_name="minor_courage",
            ),
        ),
    )

    major = analysis.for_effect("major_courage")
    minor = analysis.for_effect("minor_courage")

    assert major is not None
    assert major.is_satisfied
    assert major.providers == ("Healer One",)

    assert minor is not None
    assert minor.is_satisfied
    assert minor.providers == ("Healer Two",)