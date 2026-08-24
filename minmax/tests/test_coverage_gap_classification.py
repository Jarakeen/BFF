from minmax.coverage_classification import CoverageClassification
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


def test_coverage_analysis_classifies_single_provider_as_covered():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", "major_courage"),
    )

    result = analysis.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.COVERED
    assert result.providers == ("Healer One",)


def test_coverage_analysis_classifies_extra_unique_provider_as_redundant():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", "major_courage"),
        _provider("Healer Two", "major_courage"),
    )

    result = analysis.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.REDUNDANT
    assert result.redundant_providers == ("Healer Two",)


def test_coverage_analysis_does_not_call_stacking_provider_redundant():
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

    result = analysis.classification_for_effect("stacking_effect")

    assert result is not None
    assert result.classification == CoverageClassification.COVERED
    assert result.redundant_providers == ()


def test_coverage_analysis_classifies_missing_effect():
    analysis = _analysis("major_slayer")

    result = analysis.classification_for_effect("major_slayer")

    assert result is not None
    assert result.classification == CoverageClassification.MISSING


def test_coverage_analysis_classifies_insufficient_providers():
    analysis = _analysis(
        "major_slayer",
        _provider("DD One", "major_slayer"),
        required_provider_count=2,
    )

    result = analysis.classification_for_effect("major_slayer")

    assert result is not None
    assert result.classification == CoverageClassification.INSUFFICIENT
    assert result.valid_provider_count == 1


def test_classifications_returns_results_for_every_gap():
    analysis = CoverageGapAnalyzer().analyze(
        RosterCoverageAnalyzer().analyze(
            {
                "major_courage": (
                    _provider("Healer One", "major_courage"),
                ),
            }
        ),
        (
            CoverageRequirement(effect_name="major_courage"),
            CoverageRequirement(effect_name="major_slayer"),
        ),
    )

    classifications = analysis.classifications()

    assert len(classifications) == 2
    assert classifications[0].effect_name == "major_courage"
    assert classifications[1].effect_name == "major_slayer"


def test_classification_for_unknown_effect_returns_none():
    analysis = _analysis(
        "major_courage",
        _provider("Healer One", "major_courage"),
    )

    assert analysis.classification_for_effect("major_slayer") is None
