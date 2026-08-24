from minmax.coverage_classification import (
    CoverageClassification,
    CoverageClassificationResult,
)
from minmax.coverage_recommendation import (
    CoverageRecommendationAnalyzer,
    RecommendationAction,
)


def _result(
    classification: CoverageClassification,
    *,
    effect_name: str = "major_courage",
    providers: tuple[str, ...] = (),
    redundant_providers: tuple[str, ...] = (),
    conflicting_providers: tuple[str, ...] = (),
    required_provider_count: int = 1,
    valid_provider_count: int = 0,
) -> CoverageClassificationResult:
    return CoverageClassificationResult(
        effect_name=effect_name,
        classification=classification,
        required_provider_count=required_provider_count,
        valid_provider_count=valid_provider_count,
        providers=providers,
        redundant_providers=redundant_providers,
        conflicting_providers=conflicting_providers,
    )


def test_covered_requires_no_action():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.COVERED,
            providers=("Healer One",),
            valid_provider_count=1,
        )
    )

    assert result.action == RecommendationAction.NO_ACTION
    assert result.classification == CoverageClassification.COVERED
    assert result.providers == ("Healer One",)


def test_redundant_requires_no_correction():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.REDUNDANT,
            providers=("Healer One", "Healer Two"),
            redundant_providers=("Healer Two",),
            valid_provider_count=2,
        )
    )

    assert result.action == RecommendationAction.NO_ACTION
    assert result.classification == CoverageClassification.REDUNDANT
    assert result.redundant_providers == ("Healer Two",)


def test_missing_recommends_adding_provider():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.MISSING,
            required_provider_count=1,
        )
    )

    assert result.action == RecommendationAction.ADD_PROVIDER
    assert result.classification == CoverageClassification.MISSING


def test_insufficient_with_no_valid_provider_recommends_adding_provider():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.INSUFFICIENT,
            providers=("Healer One",),
            required_provider_count=2,
            valid_provider_count=0,
        )
    )

    assert result.action == RecommendationAction.ADD_PROVIDER


def test_insufficient_existing_provider_recommends_uptime_investigation():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.INSUFFICIENT,
            providers=("Healer One",),
            required_provider_count=2,
            valid_provider_count=1,
        )
    )

    assert result.action == RecommendationAction.INCREASE_UPTIME
    assert result.valid_provider_count == 1


def test_conflict_recommends_conflict_resolution():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.CONFLICT,
            providers=("Healer One", "Healer Two"),
            conflicting_providers=("Healer One", "Healer Two"),
            valid_provider_count=2,
        )
    )

    assert result.action == RecommendationAction.RESOLVE_CONFLICT
    assert result.conflicting_providers == (
        "Healer One",
        "Healer Two",
    )


def test_unknown_recommends_data_verification():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.UNKNOWN,
        )
    )

    assert result.action == RecommendationAction.VERIFY_DATA


def test_recommendation_preserves_requirement_counts():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.INSUFFICIENT,
            providers=("Healer One",),
            required_provider_count=3,
            valid_provider_count=1,
        )
    )

    assert result.required_provider_count == 3
    assert result.valid_provider_count == 1


def test_recommendation_preserves_effect_identity():
    result = CoverageRecommendationAnalyzer().recommend(
        _result(
            CoverageClassification.MISSING,
            effect_name="major_slayer",
        )
    )

    assert result.effect_name == "major_slayer"
    assert result.classification == CoverageClassification.MISSING
