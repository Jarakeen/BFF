from services.performance_raid_review_event_enrichment_service import (
    PerformanceRaidReviewEventEnrichmentService,
)


def test_counts_actor_deaths_and_uses_last_named_damage_as_cause() -> None:
    service = PerformanceRaidReviewEventEnrichmentService()
    result = service.enrich(
        [
            {"timestamp": 10_000, "type": "damage", "targetID": 7, "abilityName": "Ice Cage"},
            {"timestamp": 11_500, "type": "damage", "targetID": 7, "abilityName": "Glacial Fist"},
            {"timestamp": 12_000, "type": "death", "targetID": 7},
            {"timestamp": 50_000, "type": "death", "targetID": 8},
            {"timestamp": 60_000, "type": "death", "targetID": 7, "abilityName": "Frozen Prison"},
        ],
        actor_id=7,
        fight_start_time_ms=2_000,
    )

    assert result.death_count == 2
    assert result.first_death_seconds == 10.0
    assert result.first_death_ability == "Glacial Fist"


def test_explicit_death_ability_wins_over_preceding_damage() -> None:
    service = PerformanceRaidReviewEventEnrichmentService()
    result = service.enrich(
        [
            {"timestamp": 9_000, "type": "damage", "targetID": 7, "abilityName": "Earlier Hit"},
            {"timestamp": 10_000, "type": "death", "targetID": 7, "ability": {"name": "Killing Mechanic"}},
        ],
        actor_id=7,
        fight_start_time_ms=0,
    )

    assert result.first_death_ability == "Killing Mechanic"


def test_named_resource_snapshots_produce_minimum_percent() -> None:
    service = PerformanceRaidReviewEventEnrichmentService()
    result = service.enrich(
        [
            {
                "timestamp": 1_000,
                "sourceID": 7,
                "resources": [
                    {"resourceTypeName": "Magicka", "currentAmount": 18_000, "maxAmount": 30_000},
                    {"resourceTypeName": "Stamina", "currentAmount": 10_000, "maxAmount": 20_000},
                ],
            },
            {
                "timestamp": 2_000,
                "targetID": 7,
                "resources": [
                    {"resourceName": "Magicka", "current": 3_000, "maximum": 30_000},
                ],
            },
        ],
        actor_id=7,
        fight_start_time_ms=0,
        primary_resource_name="Magicka",
    )

    assert result.minimum_primary_resource_percent == 10.0
    assert result.unresolved == ()


def test_numeric_resource_type_is_not_guessed() -> None:
    service = PerformanceRaidReviewEventEnrichmentService()
    result = service.enrich(
        [
            {
                "timestamp": 1_000,
                "sourceID": 7,
                "resourceChangeType": 2,
                "resourceAmount": 3_000,
                "maxResourceAmount": 30_000,
            }
        ],
        actor_id=7,
        fight_start_time_ms=0,
        primary_resource_name="Magicka",
    )

    assert result.minimum_primary_resource_percent is None
    assert len(result.unresolved) == 1
    assert "numeric resource type IDs were not inferred" in result.unresolved[0]


def test_unrelated_actor_resource_samples_are_ignored() -> None:
    service = PerformanceRaidReviewEventEnrichmentService()
    result = service.enrich(
        [
            {
                "timestamp": 1_000,
                "sourceID": 8,
                "resources": [
                    {"resourceTypeName": "Magicka", "currentAmount": 1, "maxAmount": 100},
                ],
            },
            {
                "timestamp": 2_000,
                "sourceID": 7,
                "resources": [
                    {"resourceTypeName": "Magicka", "currentAmount": 25, "maxAmount": 100},
                ],
            },
        ],
        actor_id=7,
        fight_start_time_ms=0,
        primary_resource_name="Magicka",
    )

    assert result.minimum_primary_resource_percent == 25.0
