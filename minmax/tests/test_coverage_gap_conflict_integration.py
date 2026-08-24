from minmax.coverage_classification import CoverageClassification
from minmax.coverage_conflict import CoverageConflictAnalyzer
from minmax.coverage_gap import CoverageGapAnalyzer
from minmax.coverage_requirement import CoverageRequirement
from minmax.role import Role
from minmax.roster_capability_resolver import RosterCapabilityProvider
from minmax.roster_coverage import RosterCoverageAnalyzer
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType


def _provider(
    name: str,
    effect_name: str,
    *,
    exclusivity_group: str | None = None,
    stacking: StackingBehavior = StackingBehavior.UNIQUE,
) -> RosterCapabilityProvider:
    return RosterCapabilityProvider(
        character_name=name,
        role=Role.HEALER,
        effect=SupportEffect(
            source="Test Source",
            name=effect_name,
            category=SupportEffectCategory.BUFF,
            effect_type=effect_name,
            target_type=SupportTargetType.GROUP,
            stacking=stacking,
            exclusivity_group=exclusivity_group,
        ),
    )


def _analysis(
    effect_name: str,
    *providers: RosterCapabilityProvider,
    required_provider_count: int = 1,
):
    coverage = RosterCoverageAnalyzer().analyze(
        {
            effect_name: tuple(providers),
        }
    )

    return CoverageGapAnalyzer().analyze(
        coverage,
        (
            CoverageRequirement(
                effect_name=effect_name,
                required_provider_count=required_provider_count,
            ),
        ),
    )


def test_conflict_report_promotes_exclusivity_to_conflict():
    analysis = _analysis(
        "major_courage",
        _provider(
            "Healer One",
            "major_courage",
            exclusivity_group="major_courage",
        ),
        _provider(
            "Healer Two",
            "major_courage",
            exclusivity_group="major_courage",
        ),
    )

    conflicts = CoverageConflictAnalyzer().analyze(analysis)

    classifications = analysis.classifications(conflicts)

    assert len(classifications) == 1

    result = classifications[0]

    assert result.effect_name == "major_courage"
    assert result.classification == CoverageClassification.CONFLICT
    assert result.is_actionable_problem
    assert result.conflicting_providers == (
        "Healer One",
        "Healer Two",
    )


def test_no_conflict_report_preserves_redundancy_classification():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", "major_courage"),
        _provider("Healer Two", "major_courage"),
    )

    conflicts = CoverageConflictAnalyzer().analyze(analysis)

    classifications = analysis.classifications(conflicts)

    result = classifications[0]

    assert result.classification == CoverageClassification.REDUNDANT
    assert result.redundant_providers == ("Healer Two",)
    assert result.conflicting_providers == ()


def test_stack_providers_remain_covered_with_conflict_report():
    analysis = _analysis(
        "stacking_effect",
        _provider(
            "Healer One",
            "stacking_effect",
            stacking=StackingBehavior.STACKS,
        ),
        _provider(
            "Healer Two",
            "stacking_effect",
            stacking=StackingBehavior.STACKS,
        ),
    )

    conflicts = CoverageConflictAnalyzer().analyze(analysis)

    classifications = analysis.classifications(conflicts)

    result = classifications[0]

    assert result.classification == CoverageClassification.COVERED
    assert result.redundant_providers == ()
    assert result.conflicting_providers == ()


def test_missing_capability_remains_missing_with_conflict_report():
    analysis = _analysis("major_slayer")

    conflicts = CoverageConflictAnalyzer().analyze(analysis)

    classifications = analysis.classifications(conflicts)

    result = classifications[0]

    assert result.classification == CoverageClassification.MISSING
    assert result.is_actionable_problem


def test_insufficient_capability_remains_insufficient_with_conflict_report():
    analysis = _analysis(
        "major_slayer",
        _provider("DD One", "major_slayer"),
        required_provider_count=2,
    )

    conflicts = CoverageConflictAnalyzer().analyze(analysis)

    classifications = analysis.classifications(conflicts)

    result = classifications[0]

    assert result.classification == CoverageClassification.INSUFFICIENT
    assert result.valid_provider_count == 1


def test_cross_effect_exclusivity_is_promoted_to_conflict():
    coverage = RosterCoverageAnalyzer().analyze(
        {
            "effect_a": (
                _provider(
                    "Healer One",
                    "effect_a",
                    exclusivity_group="courage",
                ),
            ),
            "effect_b": (
                _provider(
                    "Healer Two",
                    "effect_b",
                    exclusivity_group="courage",
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

    conflicts = CoverageConflictAnalyzer().analyze(analysis)

    classifications = analysis.classifications(conflicts)

    assert len(classifications) == 2

    assert all(
        result.classification == CoverageClassification.CONFLICT
        for result in classifications
    )

    assert classifications[0].conflicting_providers == ("Healer One",)
    assert classifications[1].conflicting_providers == ("Healer Two",)


def test_classification_for_effect_accepts_conflict_report():
    analysis = _analysis(
        "major_courage",
        _provider(
            "Healer One",
            "major_courage",
            exclusivity_group="major_courage",
        ),
        _provider(
            "Healer Two",
            "major_courage",
            exclusivity_group="major_courage",
        ),
    )

    conflicts = CoverageConflictAnalyzer().analyze(analysis)

    result = analysis.classification_for_effect(
        "major_courage",
        conflicts,
    )

    assert result is not None
    assert result.classification == CoverageClassification.CONFLICT
