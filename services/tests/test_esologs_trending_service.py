from services.esologs_client import EsoLogsApiError
from services.esologs_trending_service import EsoLogsTrendingService


class _TrendingClient:
    def __init__(self):
        self.report_candidates = [("A", 1), ("B", 2), ("C", 3)]

    def get_trial_zones(self):
        return [
            {
                "id": 1,
                "name": "Sunspire",
                "encounters": [{"id": 99, "name": "Nahviintaas"}],
            }
        ]

    def get_top_reports_for_encounter(self, encounter_id, limit=5):
        assert encounter_id == 99
        return self.report_candidates[:limit]

    def get_fight(self, report_code, fight_id):
        return {"startTime": 0, "endTime": 10_000}

    def get_report_player_summary(self, report_code, fight_id, start, end):
        if report_code == "C":
            raise EsoLogsApiError("private")

        if report_code == "A":
            return {
                "tanks": [
                    {
                        "name": "TankA",
                        "type": "Dragonknight",
                        "combatantInfo": {
                            "gear": [
                                {"setName": "Pearlescent Ward"},
                                {"setName": "Turning Tide"},
                                {"setName": "Pearlescent Ward"},
                            ]
                        },
                    }
                ],
                "healers": [
                    {
                        "name": "HealA",
                        "type": "Warden",
                        "combatantInfo": {
                            "gear": [
                                {"setName": "Spell Power Cure"},
                                {"setName": "Pillager's Profit"},
                            ]
                        },
                    }
                ],
                "dps": [
                    {
                        "name": "DDA",
                        "type": "Arcanist",
                        "combatantInfo": {
                            "gear": [
                                {"setName": "Coral Riptide"},
                                {"setName": "Deadly Strike"},
                            ]
                        },
                    },
                    {
                        "name": "DDB",
                        "type": "Arcanist",
                        "combatantInfo": {
                            "gear": [
                                {"setName": "Coral Riptide"},
                                {"setName": "Deadly Strike"},
                            ]
                        },
                    },
                ],
            }

        return {
            "tanks": [
                {
                    "name": "TankB",
                    "type": "Necromancer",
                    "combatantInfo": {
                        "gear": [
                            {"setName": "Pearlescent Ward"},
                            {"setName": "Lucent Echoes"},
                        ]
                    },
                }
            ],
            "healers": [
                {
                    "name": "HealB",
                    "type": "Warden",
                    "combatantInfo": {
                        "gear": [
                            {"setName": "Spell Power Cure"},
                            {"setName": "Roaring Opportunist"},
                        ]
                    },
                }
            ],
            "dps": [
                {
                    "name": "DDC",
                    "type": "Arcanist",
                    "combatantInfo": {
                        "gear": [
                            {"setName": "Coral Riptide"},
                            {"setName": "Ansuul's Torment"},
                        ]
                    },
                }
            ],
        }


def test_trending_aggregates_distinct_set_usage_by_role():
    report = EsoLogsTrendingService(_TrendingClient()).analyze_encounter(
        zone_id=1,
        zone_name="Sunspire",
        encounter_id=99,
        encounter_name="Nahviintaas",
        report_limit=3,
    )

    assert report.reports_analyzed == 2
    assert report.reports_skipped == 1
    assert report.players_analyzed == 7

    dd = report.role_summaries["dps"]
    assert dd.player_count == 3
    assert [(row.name, row.count) for row in dd.gear_sets[:3]] == [
        ("Coral Riptide", 3),
        ("Deadly Strike", 2),
        ("Ansuul's Torment", 1),
    ]
    assert dd.gear_sets[0].percent == 100.0
    assert [(row.name, row.count) for row in dd.classes] == [("Arcanist", 3)]

    healer = report.role_summaries["healer"]
    assert healer.gear_sets[0].name == "Spell Power Cure"
    assert healer.gear_sets[0].count == 2

    tank = report.role_summaries["tank"]
    assert tank.gear_sets[0].name == "Pearlescent Ward"
    assert tank.gear_sets[0].count == 2


def test_trending_does_not_count_duplicate_equipped_pieces_as_multiple_players():
    report = EsoLogsTrendingService(_TrendingClient()).analyze_encounter(
        zone_id=1,
        zone_name="Sunspire",
        encounter_id=99,
        encounter_name="Nahviintaas",
        report_limit=1,
    )

    tank = report.role_summaries["tank"]
    pearlescent = next(row for row in tank.gear_sets if row.name == "Pearlescent Ward")
    assert pearlescent.count == 1
    assert pearlescent.player_count == 1
    assert pearlescent.percent == 100.0


def test_trending_fails_when_no_ranked_report_is_usable():
    class _BrokenClient(_TrendingClient):
        def get_report_player_summary(self, report_code, fight_id, start, end):
            raise EsoLogsApiError("private")

    try:
        EsoLogsTrendingService(_BrokenClient()).analyze_encounter(
            zone_id=1,
            zone_name="Sunspire",
            encounter_id=99,
            encounter_name="Nahviintaas",
            report_limit=3,
        )
    except EsoLogsApiError as exc:
        assert "Could not load usable ranked reports" in str(exc)
    else:
        raise AssertionError("Expected EsoLogsApiError")
