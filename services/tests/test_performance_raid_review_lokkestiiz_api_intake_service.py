from __future__ import annotations

from types import SimpleNamespace

from models.performance_model import ActorChoice
from services.performance_raid_review_lokkestiiz_api_intake_service import (
    PerformanceRaidReviewLokkestiizApiIntakeService,
)


class _Client:
    def __init__(self, *, actors=None, fights=None):
        self.actors = (
            [
                {"id": 900, "name": "Lokkestiiz", "type": "NPC", "subType": "Boss"},
            ]
            if actors is None
            else actors
        )
        self.fights = fights or {
            3: {"id": 3, "name": "Lokkestiiz"},
            4: {"id": 4, "name": "Lokkestiiz"},
        }
        self.queries = []

    @staticmethod
    def normalize_report_code(value):
        return str(value).rstrip("/").split("/")[-1]

    def _query(self, query, variables):
        self.queries.append((query, variables))
        return {"reportData": {"report": {"masterData": {"actors": self.actors}}}}

    def get_fight(self, report_code, fight_id):
        if fight_id not in self.fights:
            raise ValueError("missing fight")
        return self.fights[fight_id]


class _PerformanceService:
    def __init__(self, client):
        self.client = client

    def list_actors(self, report_code, fight_id):
        return (
            {"name": "Lokkestiiz"},
            [
                ActorChoice(ActorId=11, Label="Tank One", Role="Tank"),
                ActorChoice(ActorId=12, Label="Heal One", Role="Healer"),
                ActorChoice(ActorId=13, Label="DD One", Role="DPS"),
            ],
        )


def test_builds_multiple_pull_requests_directly_from_one_report() -> None:
    service = PerformanceRaidReviewLokkestiizApiIntakeService(_PerformanceService(_Client()))

    result = service.build("ABC123", [3, 4])

    assert [row.fight_id for row in result.pulls] == [3, 4]
    assert all(row.report_code == "ABC123" for row in result.pulls)
    assert all(row.boss_actor_id == 900 for row in result.pulls)
    assert result.pulls[0].sources[0].member_key == "abc123:11"
    assert result.pulls[1].sources[0].member_key == "abc123:11"
    assert result.unresolved == ()


def test_normalizes_report_url_and_deduplicates_selected_fights() -> None:
    service = PerformanceRaidReviewLokkestiizApiIntakeService(_PerformanceService(_Client()))

    result = service.build("https://www.esologs.com/reports/ABC123", [3, 3])

    assert len(result.pulls) == 1
    assert result.pulls[0].report_code == "ABC123"


def test_skips_non_lokkestiiz_fight_without_poisoning_other_pulls() -> None:
    client = _Client(fights={
        3: {"id": 3, "name": "Lokkestiiz"},
        4: {"id": 4, "name": "Yolnahkriin"},
    })
    service = PerformanceRaidReviewLokkestiizApiIntakeService(_PerformanceService(client))

    result = service.build("ABC123", [3, 4])

    assert [row.fight_id for row in result.pulls] == [3]
    assert any("not Lokkestiiz" in item for item in result.unresolved)


def test_missing_or_ambiguous_named_boss_actor_fails_closed() -> None:
    missing = PerformanceRaidReviewLokkestiizApiIntakeService(
        _PerformanceService(_Client(actors=[]))
    ).build("ABC123", [3])
    assert missing.pulls == ()
    assert any("did not contain a named Lokkestiiz boss actor" in item for item in missing.unresolved)

    ambiguous = PerformanceRaidReviewLokkestiizApiIntakeService(
        _PerformanceService(_Client(actors=[
            {"id": 900, "name": "Lokkestiiz", "type": "NPC", "subType": "Boss"},
            {"id": 901, "name": "Lokkestiiz", "type": "NPC", "subType": "Boss"},
        ]))
    ).build("ABC123", [3])
    assert ambiguous.pulls == ()
    assert any("2 distinct" in item for item in ambiguous.unresolved)


def test_rejects_empty_selection_and_keeps_report_scoped_identity() -> None:
    service = PerformanceRaidReviewLokkestiizApiIntakeService(_PerformanceService(_Client()))

    empty = service.build("ABC123", [])
    assert empty.pulls == ()
    assert any("No positive fight IDs" in item for item in empty.unresolved)

    result = service.build("ABC123", [3])
    keys = {source.member_key for source in result.pulls[0].sources}
    assert keys == {"abc123:11", "abc123:12", "abc123:13"}
