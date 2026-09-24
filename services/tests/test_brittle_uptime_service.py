from __future__ import annotations

from services.brittle_uptime_service import BrittleUptimeService


class _FakeClient:
    def normalize_report_code(self, value):
        return str(value).split("/")[-1]

    def get_fights(self, code):
        return [
            {"id": 6, "name": "Boss", "kill": True, "startTime": 0, "endTime": 100000},
            {"id": 7, "name": "Boss", "kill": False, "startTime": 0, "endTime": 80000},
        ]

    def get_report_player_summary(self, code, fight_id, start, end):
        return {
            "healers": [{"id": 72, "name": "", "anonymous": True}],
            "dps": [{"id": 9, "name": "Other"}],
        }

    def get_aura_table(self, code, fight_id, start, end, **kwargs):
        source_id = kwargs.get("source_id")
        if source_id == 72:
            return [
                {"name": "Minor Brittle", "guid": 145975, "totalUptime": 61000},
                {"name": "Minor Brittle", "guid": 146697, "totalUptime": 61000},
            ]
        if source_id == 9:
            return [{"name": "Minor Brittle", "totalUptime": 12000}]
        return [
            {"name": "Minor Brittle", "guid": 145975, "totalUptime": 87000},
            {"name": "Minor Brittle", "guid": 146697, "totalUptime": 87000},
        ]


def test_duplicate_minor_brittle_ids_are_not_summed():
    assert BrittleUptimeService._named_uptime_ms(
        [
            {"name": "Minor Brittle", "totalUptime": 50000},
            {"name": "Minor Brittle", "totalUptime": 50000},
        ]
    ) == 50000


def test_report_compares_raid_and_provider_uptime():
    result = BrittleUptimeService(_FakeClient()).analyze(
        "REPORT",
        fight_ids=(6,),
        kills_only=True,
    )

    assert len(result.fights) == 1
    fight = result.fights[0]
    assert fight.brittle_seconds == 87.0
    assert fight.brittle_percent == 87.0
    assert fight.providers[0].actor_label == "Anonymous 72"
    assert fight.providers[0].uptime_percent == 61.0
    assert result.average_percent == 87.0


def test_kills_only_filters_wipes_when_no_explicit_fight_ids():
    result = BrittleUptimeService(_FakeClient()).analyze("REPORT", kills_only=True)
    assert [row.fight_id for row in result.fights] == [6]
