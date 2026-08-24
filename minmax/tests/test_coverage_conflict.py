from minmax.coverage_conflict import (
    ConflictType,
    CoverageConflictAnalyzer,
)
from minmax.coverage_gap import CoverageGapAnalyzer, CoverageStatus
from minmax.coverage_requirement import CoverageRequirement
from minmax.role import Role
from minmax.roster_capability_resolver import RosterCapabilityProvider
from minmax.roster_coverage import RosterCoverageAnalyzer
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType


def _effect(
    name: str,
    *,
    stacking: StackingBehavior = StackingBehavior.UNIQUE,
    exclusivity_group: str | None = None,
) -> SupportEffect:
    return SupportEffect(
        source="Test Source",
        name=name,
        category=SupportEffectCategory.BUFF,
        effect_type=name,
        target_type=SupportTargetType.GROUP,
        stacking=stacking,
        exclusivity_group=exclusivity_group,
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


def _analysis(
    effect_name: str,
    *providers: RosterCapabilityProvider,
):
    coverage = RosterCoverageAnalyzer().analyze(
        {effect_name: tuple(providers)}
    )

    return CoverageGapAnalyzer().analyze(
        coverage,
        (CoverageRequirement(effect_name=effect_name),),
    )


def test_no_conflict_for_single_provider():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", _effect("major_courage")),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert report.conflicts == ()
    assert report.redundancies == ()
    assert report.exclusivities == ()


def test_multiple_valid_providers_are_reported_as_redundancy():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", _effect("major_courage")),
        _provider("Healer Two", _effect("major_courage")),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert len(report.redundancies) == 1

    redundancy = report.redundancies[0]

    assert redundancy.effect_name == "major_courage"
    assert redundancy.conflict_type == ConflictType.REDUNDANCY
    assert redundancy.providers == ("Healer Two",)


def test_redundancy_is_not_exclusivity_without_group():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", _effect("major_courage")),
        _provider("Healer Two", _effect("major_courage")),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert len(report.redundancies) == 1
    assert report.exclusivities == ()


def test_same_exclusivity_group_is_reported():
    analysis = _analysis(
        "major_courage",
        _provider(
            "Healer One",
            _effect(
                "major_courage",
                exclusivity_group="major_courage",
            ),
        ),
        _provider(
            "Healer Two",
            _effect(
                "major_courage",
                exclusivity_group="major_courage",
            ),
        ),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert len(report.exclusivities) == 1

    conflict = report.exclusivities[0]

    assert conflict.effect_name is None
    assert conflict.conflict_type == ConflictType.EXCLUSIVITY
    assert conflict.providers == (
        "Healer One",
        "Healer Two",
    )
    assert conflict.exclusivity_group == "major_courage"


def test_different_exclusivity_groups_do_not_conflict():
    analysis = _analysis(
        "major_courage",
        _provider(
            "Healer One",
            _effect(
                "major_courage",
                exclusivity_group="group_a",
            ),
        ),
        _provider(
            "Healer Two",
            _effect(
                "major_courage",
                exclusivity_group="group_b",
            ),
        ),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert len(report.redundancies) == 1
    assert report.exclusivities == ()


def test_gap_retains_full_provider_evidence():
    provider = _provider(
        "Healer One",
        _effect(
            "major_courage",
            exclusivity_group="major_courage",
        ),
    )

    analysis = _analysis(
        "major_courage",
        provider,
    )

    gap = analysis.for_effect("major_courage")

    assert gap is not None
    assert gap.status == CoverageStatus.COVERED

    # Public compatibility API remains name-based.
    assert gap.providers == ("Healer One",)
    assert gap.satisfying_providers == ("Healer One",)

    # Full mechanical evidence survives the coverage boundary.
    assert len(gap.provider_evidence) == 1

    evidence = gap.provider_evidence[0]

    assert evidence.character_name == "Healer One"
    assert evidence.role == Role.HEALER
    assert evidence.effect == provider.effect
    assert evidence.effect.exclusivity_group == "major_courage"

    assert len(gap.satisfying_provider_evidence) == 1
    assert gap.satisfying_provider_evidence[0] == evidence


def test_conflict_report_can_filter_by_effect():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", _effect("major_courage")),
        _provider("Healer Two", _effect("major_courage")),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert len(report.for_effect("major_courage")) == 1
    assert report.for_effect("major_slayer") == ()


def test_two_required_providers_are_not_redundant():
    coverage = RosterCoverageAnalyzer().analyze(
        {
            "major_courage": (
                _provider("Healer One", _effect("major_courage")),
                _provider("Healer Two", _effect("major_courage")),
            ),
        }
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

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert report.redundancies == ()


def test_stacking_effect_providers_are_not_automatically_redundant():
    coverage = RosterCoverageAnalyzer().analyze(
        {
            "test_stack": (
                _provider(
                    "Healer One",
                    _effect(
                        "test_stack",
                        stacking=StackingBehavior.STACKS,
                    ),
                ),
                _provider(
                    "Healer Two",
                    _effect(
                        "test_stack",
                        stacking=StackingBehavior.STACKS,
                    ),
                ),
            ),
        }
    )

    analysis = CoverageGapAnalyzer().analyze(
        coverage,
        (
            CoverageRequirement(
                effect_name="test_stack",
                required_provider_count=1,
            ),
        ),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    assert report.redundancies == ()


def test_same_exclusivity_group_across_different_effects_is_reported():
    coverage = RosterCoverageAnalyzer().analyze(
        {
            "effect_a": (
                _provider(
                    "Healer One",
                    _effect(
                        "effect_a",
                        exclusivity_group="courage",
                    ),
                ),
            ),
            "effect_b": (
                _provider(
                    "Healer Two",
                    _effect(
                        "effect_b",
                        exclusivity_group="courage",
                    ),
                ),
            ),
        }
    )

    analysis = CoverageGapAnalyzer().analyze(
        coverage,
        (
            CoverageRequirement(effect_name="effect_a"),
            CoverageRequirement(effect_name="effect_b"),
        ),
    )

    report = CoverageConflictAnalyzer().analyze(analysis)

    exclusivities = report.exclusivities

    assert len(exclusivities) == 1

    conflict = exclusivities[0]

    assert conflict.effect_name is None
    assert conflict.conflict_type == ConflictType.EXCLUSIVITY
    assert conflict.exclusivity_group == "courage"
    assert conflict.providers == (
        "Healer One",
        "Healer Two",
    )
