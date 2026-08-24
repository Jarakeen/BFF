from minmax.coverage_classification import (
    CoverageClassification,
    CoverageClassificationAnalyzer,
)


def test_single_valid_provider_is_covered():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="major_courage",
        required_provider_count=1,
        providers=("Healer One",),
        satisfying_providers=("Healer One",),
    )

    assert result.classification == CoverageClassification.COVERED
    assert result.is_satisfied
    assert not result.is_actionable_problem


def test_extra_provider_is_redundant():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="major_courage",
        required_provider_count=1,
        providers=("Healer One", "Healer Two"),
        satisfying_providers=("Healer One", "Healer Two"),
        redundant_providers=("Healer Two",),
    )

    assert result.classification == CoverageClassification.REDUNDANT
    assert result.redundant_providers == ("Healer Two",)
    assert result.is_satisfied


def test_required_two_providers_are_covered():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="major_courage",
        required_provider_count=2,
        providers=("Healer One", "Healer Two"),
        satisfying_providers=("Healer One", "Healer Two"),
    )

    assert result.classification == CoverageClassification.COVERED
    assert result.valid_provider_count == 2


def test_no_provider_is_missing():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="major_slayer",
        required_provider_count=1,
        providers=(),
        satisfying_providers=(),
    )

    assert result.classification == CoverageClassification.MISSING
    assert result.is_actionable_problem


def test_provider_exists_but_does_not_satisfy_requirement_is_insufficient():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="major_slayer",
        required_provider_count=1,
        providers=("DD One",),
        satisfying_providers=(),
    )

    assert result.classification == CoverageClassification.INSUFFICIENT
    assert result.providers == ("DD One",)


def test_fewer_valid_providers_than_required_is_insufficient():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="major_slayer",
        required_provider_count=2,
        providers=("DD One",),
        satisfying_providers=("DD One",),
    )

    assert result.classification == CoverageClassification.INSUFFICIENT
    assert result.valid_provider_count == 1


def test_conflict_is_actionable_problem():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="effect_a",
        required_provider_count=1,
        providers=("Healer One", "Healer Two"),
        satisfying_providers=("Healer One", "Healer Two"),
        conflicting_providers=("Healer One", "Healer Two"),
    )

    assert result.classification == CoverageClassification.CONFLICT
    assert result.conflicting_providers == (
        "Healer One",
        "Healer Two",
    )
    assert result.is_actionable_problem


def test_unknown_is_not_claimed_by_default():
    result = CoverageClassificationAnalyzer().classify(
        effect_name="major_slayer",
        required_provider_count=1,
        providers=("DD One",),
        satisfying_providers=("DD One",),
    )

    assert result.classification != CoverageClassification.UNKNOWN


def test_invalid_provider_requirement_is_rejected():
    try:
        CoverageClassificationAnalyzer().classify(
            effect_name="major_slayer",
            required_provider_count=0,
            providers=(),
            satisfying_providers=(),
        )
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for invalid required_provider_count."
        )


def test_report_filters_problems_and_satisfied_results():
    analyzer = CoverageClassificationAnalyzer()

    report = __import__(
        "minmax.coverage_classification",
        fromlist=["CoverageClassificationReport"],
    ).CoverageClassificationReport(
        (
            analyzer.classify(
                effect_name="major_courage",
                required_provider_count=1,
                providers=("Healer One",),
                satisfying_providers=("Healer One",),
            ),
            analyzer.classify(
                effect_name="major_slayer",
                required_provider_count=1,
                providers=(),
                satisfying_providers=(),
            ),
        )
    )

    assert len(report.satisfied) == 1
    assert report.satisfied[0].effect_name == "major_courage"

    assert len(report.problems) == 1
    assert report.problems[0].effect_name == "major_slayer"

    assert report.for_effect("major_courage") is not None
    assert report.for_effect("missing") is None
