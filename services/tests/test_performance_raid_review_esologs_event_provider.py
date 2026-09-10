from services.performance_raid_review_esologs_event_provider import (
    PerformanceRaidReviewEsoLogsEventProvider,
)
from services.performance_raid_review_observation_service import RaidReviewSource


class _Client:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def _query(self, query, variables):
        self.calls.append((query, dict(variables)))
        if not self.pages:
            raise AssertionError("unexpected extra ESO Logs event query")
        return self.pages.pop(0)


def _page(rows, next_timestamp=None):
    return {
        "reportData": {
            "report": {
                "events": {
                    "data": rows,
                    "nextPageTimestamp": next_timestamp,
                }
            }
        }
    }


def _fight():
    return {"startTime": 1000.0, "endTime": 11000.0}


def test_provider_paginates_then_reuses_fight_cache_for_other_actor() -> None:
    client = _Client(
        [
            _page(
                [
                    {
                        "timestamp": 2000.0,
                        "type": "damage",
                        "targetID": 7,
                        "abilityName": "Ice",
                    }
                ],
                next_timestamp=6000.0,
            ),
            _page(
                [
                    {
                        "timestamp": 3000.0,
                        "type": "death",
                        "targetID": 7,
                    },
                    {
                        "timestamp": 4000.0,
                        "type": "death",
                        "targetID": 8,
                    },
                ]
            ),
        ]
    )
    provider = PerformanceRaidReviewEsoLogsEventProvider(client)

    first = provider.resolve(
        RaidReviewSource("A", 1, 7, "Healer", "Healer"),
        _fight(),
    )
    second = provider.resolve(
        RaidReviewSource("A", 1, 8, "Tank", "Tank"),
        _fight(),
    )

    assert first.death_count == 1
    assert first.first_death_seconds == 2.0
    assert first.first_death_ability == "Ice"
    assert second.death_count == 1
    assert len(client.calls) == 2
    assert client.calls[0][1]["startTime"] == 1000.0
    assert client.calls[1][1]["startTime"] == 6000.0


def test_public_fight_event_contract_reuses_same_cached_stream_as_enrichment() -> None:
    rows = [
        {"timestamp": 2500.0, "type": "death", "targetID": 7},
        {"timestamp": 3000.0, "type": "cast", "sourceID": 8, "abilityName": "Aggressive Horn"},
    ]
    client = _Client([_page(rows)])
    provider = PerformanceRaidReviewEsoLogsEventProvider(client)

    events = provider.events_for_fight(
        report_code="A",
        fight_id=1,
        start_time=1000.0,
        end_time=11000.0,
    )
    enrichment = provider.resolve(
        RaidReviewSource("A", 1, 7, "Healer", "Healer"),
        _fight(),
    )
    repeated = provider.events_for_fight(
        report_code="A",
        fight_id=1,
        start_time=1000.0,
        end_time=11000.0,
    )

    assert events == tuple(rows)
    assert repeated is events
    assert enrichment.death_count == 1
    assert len(client.calls) == 1


def test_provider_decodes_json_scalar_event_payload() -> None:
    client = _Client(
        [
            _page(
                '[{"timestamp":2500,"type":"death","targetID":7}]'
            )
        ]
    )
    provider = PerformanceRaidReviewEsoLogsEventProvider(client)

    result = provider.resolve(
        RaidReviewSource("A", 1, 7, "Healer", "Healer"),
        _fight(),
    )

    assert result.death_count == 1
    assert result.first_death_seconds == 1.5


def test_provider_rejects_incomplete_pagination_instead_of_using_partial_events() -> None:
    client = _Client(
        [
            _page(
                [{"timestamp": 2000.0, "type": "damage", "targetID": 7}],
                next_timestamp=3000.0,
            )
        ]
    )
    provider = PerformanceRaidReviewEsoLogsEventProvider(client, max_pages=1)

    try:
        provider.resolve(
            RaidReviewSource("A", 1, 7, "Healer", "Healer"),
            _fight(),
        )
    except RuntimeError as exc:
        assert "pagination exceeded" in str(exc)
    else:
        raise AssertionError("partial event evidence must not be accepted")


def test_provider_rejects_invalid_fight_clock() -> None:
    provider = PerformanceRaidReviewEsoLogsEventProvider(_Client([]))

    try:
        provider.resolve(
            RaidReviewSource("A", 1, 7, "Healer", "Healer"),
            {"startTime": 5000.0, "endTime": 5000.0},
        )
    except ValueError as exc:
        assert "invalid start/end timestamps" in str(exc)
    else:
        raise AssertionError("invalid fight clocks must fail closed")
