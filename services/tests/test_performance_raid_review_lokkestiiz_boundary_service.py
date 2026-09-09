from services.performance_raid_review_lokkestiiz_boundary_service import (
    PerformanceRaidReviewLokkestiizBoundaryService,
)


def _cast(timestamp: float, ability_id: int) -> dict:
    return {
        "type": "cast",
        "timestamp": timestamp,
        "abilityGameID": ability_id,
    }


def _damage(timestamp: float, *, target_id: int = 99, amount: float = 1000.0) -> dict:
    return {
        "type": "damage",
        "timestamp": timestamp,
        "targetID": target_id,
        "amount": amount,
    }


def test_extracts_semantic_begin_and_first_damage_after_long_gap() -> None:
    service = PerformanceRaidReviewLokkestiizBoundaryService(
        minimum_qualifying_damage_gap_seconds=30.0
    )
    result = service.extract(
        [
            _cast(20_000.0, 122820),
            _damage(20_500.0),
            _damage(21_024.0),
            _damage(72_683.0),
            _damage(73_000.0),
        ],
        boss_actor_id=99,
        fight_start_time_ms=0.0,
        evidence_source="report ABC fight 22",
    )

    assert result.unresolved == ()
    assert [(item.boundary, item.occurrence) for item in result.boundaries] == [
        ("begin", 1),
        ("end", 1),
    ]
    assert result.boundaries[0].time_seconds == 20.0
    assert result.boundaries[1].time_seconds == 72.683
    assert all(item.fact_key == "aerial_onslaught_flight" for item in result.boundaries)
    assert all(item.encounter_id == "lokkestiiz" for item in result.boundaries)


def test_damage_to_other_targets_does_not_end_flight() -> None:
    result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        [
            _cast(20_000.0, 122820),
            _damage(21_000.0, target_id=99),
            _damage(60_000.0, target_id=77),
            _damage(72_000.0, target_id=99),
        ],
        boss_actor_id=99,
        fight_start_time_ms=0.0,
        evidence_source="fixture",
    )

    assert result.boundaries[-1].time_seconds == 72.0


def test_non_positive_boss_damage_is_not_targetability_resumption() -> None:
    result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        [
            _cast(20_000.0, 122820),
            _damage(21_000.0),
            _damage(72_000.0, amount=0.0),
            _damage(73_000.0, amount=500.0),
        ],
        boss_actor_id=99,
        fight_start_time_ms=0.0,
        evidence_source="fixture",
    )

    assert result.boundaries[-1].time_seconds == 73.0


def test_partial_wipe_keeps_missing_landing_unresolved() -> None:
    result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        [
            _cast(20_000.0, 122820),
            _damage(21_000.0),
        ],
        boss_actor_id=99,
        fight_start_time_ms=0.0,
        evidence_source="wipe",
    )

    assert [(item.boundary, item.occurrence) for item in result.boundaries] == [("begin", 1)]
    assert "No qualifying boss-damage resumption" in result.unresolved[0]


def test_three_reviewed_entry_signatures_produce_three_occurrences() -> None:
    result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        [
            _cast(20_000.0, 122820),
            _damage(21_000.0),
            _damage(72_000.0),
            _cast(97_000.0, 122821),
            _damage(98_000.0),
            _damage(162_000.0),
            _cast(184_000.0, 122822),
            _damage(185_000.0),
            _damage(248_000.0),
        ],
        boss_actor_id=99,
        fight_start_time_ms=0.0,
        evidence_source="kill",
    )

    assert result.unresolved == ()
    assert [(item.boundary, item.occurrence) for item in result.boundaries] == [
        ("begin", 1), ("end", 1),
        ("begin", 2), ("end", 2),
        ("begin", 3), ("end", 3),
    ]


def test_duplicate_entry_signature_is_not_silently_selected() -> None:
    result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        [
            _cast(20_000.0, 122820),
            _cast(20_100.0, 122820),
            _damage(21_000.0),
            _damage(72_000.0),
        ],
        boss_actor_id=99,
        fight_start_time_ms=0.0,
        evidence_source="fixture",
    )

    assert result.boundaries == ()
    assert "Multiple reviewed Lokkestiiz flight-entry signatures" in result.unresolved[0]


def test_unreviewed_numeric_ability_does_not_become_canonical_boundary() -> None:
    result = PerformanceRaidReviewLokkestiizBoundaryService().extract(
        [
            _cast(20_000.0, 999999),
            _damage(21_000.0),
            _damage(72_000.0),
        ],
        boss_actor_id=99,
        fight_start_time_ms=0.0,
        evidence_source="fixture",
    )

    assert result.boundaries == ()
    assert "No reviewed Lokkestiiz flight-entry evidence signatures" in result.unresolved[0]
