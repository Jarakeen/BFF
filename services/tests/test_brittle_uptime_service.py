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
            "dps": [{"id": 9, "name": "Named Provider"}],
        }

    def get_aura_table(self, code, fight_id, start, end, **kwargs):
        source_id = kwargs.get("source_id")
        if source_id == 72:
            return [
                {"name": "Major Brittle", "guid": 145975, "totalUptime": 61000},
                {"name": "Major Brittle", "guid": 146697, "totalUptime": 61000},
            ]
        if source_id == 9:
            return [{"name": "Major Brittle", "totalUptime": 12000}]
        return [
            {"name": "Major Brittle", "guid": 145975, "totalUptime": 87000},
            {"name": "Major Brittle", "guid": 146697, "totalUptime": 87000},
        ]


def test_duplicate_major_brittle_ids_are_not_summed():
    assert BrittleUptimeService._named_uptime_ms(
        [
            {"name": "Major Brittle", "totalUptime": 50000},
            {"name": "Major Brittle", "totalUptime": 50000},
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
    assert fight.brittle_seconds == 61.0
    assert fight.brittle_percent == 61.0
    assert fight.raid_brittle_seconds == 87.0
    assert fight.raid_brittle_percent == 87.0
    assert len(fight.providers) == 1
    assert fight.providers[0].actor_id == 72
    assert fight.providers[0].actor_label == "Anonymous 72"
    assert fight.providers[0].uptime_percent == 61.0
    assert result.average_percent == 61.0


def test_kills_only_filters_wipes_when_no_explicit_fight_ids():
    result = BrittleUptimeService(_FakeClient()).analyze("REPORT", kills_only=True)
    assert [row.fight_id for row in result.fights] == [6]


def test_other_major_brittle_sources_are_not_included_as_monitored_provider():
    client = _FakeClient()
    result = BrittleUptimeService(client).analyze("REPORT", fight_ids=(6,))
    assert [row.actor_id for row in result.fights[0].providers] == [72]


def test_actor_id_can_change_per_report_and_resolves_visible_name():
    result = BrittleUptimeService(_FakeClient()).analyze(
        "REPORT",
        fight_ids=(6,),
        provider_actor_id=9,
    )

    fight = result.fights[0]
    assert fight.brittle_seconds == 12.0
    assert fight.brittle_percent == 12.0
    assert fight.providers[0].actor_id == 9
    assert fight.providers[0].actor_label == "Named Provider"


def test_source_major_brittle_falls_back_to_raw_events_when_aura_table_is_zero() -> None:
    class Client:
        @staticmethod
        def normalize_report_code(value):
            return value

        @staticmethod
        def get_fights(_code):
            return [{
                "id": 32,
                "name": "Z'Maja",
                "kill": True,
                "startTime": 1000.0,
                "endTime": 11000.0,
            }]

        @staticmethod
        def get_aura_table(*_args, **kwargs):
            if kwargs.get("source_id") is not None:
                return []
            return [{"name": "Major Brittle", "guid": 145977, "totalUptime": 4000.0}]

        @staticmethod
        def get_report_player_summary(*_args, **_kwargs):
            return {
                "playerDetails": {
                    "healers": [{"id": 72, "name": "Anonymous 72"}]
                }
            }

        @staticmethod
        def _query(_query, variables):
            # Raw Debuffs events prove source 72 applied Major Brittle for 4 seconds.
            return {
                "reportData": {
                    "report": {
                        "events": {
                            "data": [
                                {
                                    "timestamp": 2000.0,
                                    "type": "applydebuff",
                                    "sourceID": 72,
                                    "targetID": 13,
                                    "abilityGameID": 145977,
                                },
                                {
                                    "timestamp": 6000.0,
                                    "type": "removedebuff",
                                    "sourceID": 72,
                                    "targetID": 13,
                                    "abilityGameID": 145977,
                                },
                            ],
                            "nextPageTimestamp": None,
                        }
                    }
                }
            }

    result = BrittleUptimeService(Client()).analyze(
        "report",
        fight_ids=(32,),
        provider_actor_id=72,
    )

    assert result.fights[0].brittle_seconds == 4.0
    assert result.fights[0].brittle_percent == 40.0
    assert result.fights[0].providers[0].actor_id == 72
