from minmax.rotation_opportunity_band import (
    RotationOpportunitySample,
    classify_rotation_opportunity_bands,
)


def test_empty_samples_produce_no_bands() -> None:
    assert classify_rotation_opportunity_bands(()) == ()


def test_adjacent_equal_signatures_collapse_into_one_band() -> None:
    bands = classify_rotation_opportunity_bands(
        (
            RotationOpportunitySample(1.2, "harmful"),
            RotationOpportunitySample(1.3, "harmful"),
            RotationOpportunitySample(1.4, "neutral"),
            RotationOpportunitySample(1.5, "helpful"),
            RotationOpportunitySample(1.6, "helpful"),
        )
    )

    assert [(b.start_value, b.end_value, b.signature, b.sample_count) for b in bands] == [
        (1.2, 1.3, "harmful", 2),
        (1.4, 1.4, "neutral", 1),
        (1.5, 1.6, "helpful", 2),
    ]


def test_separated_equal_signatures_remain_separate_bands() -> None:
    bands = classify_rotation_opportunity_bands(
        (
            RotationOpportunitySample(1, "helpful"),
            RotationOpportunitySample(2, "neutral"),
            RotationOpportunitySample(3, "helpful"),
        )
    )

    assert len(bands) == 3
    assert bands[0].signature == "helpful"
    assert bands[2].signature == "helpful"
