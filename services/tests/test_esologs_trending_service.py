from services.esologs_client import EsoLogsApiError
from services.esologs_trending_service import EsoLogsTrendingService


class _TrendingClient:
    def __init__(self):
        self.summary_calls = []
        self.ranking_calls = []
        self.rankings = {
            "DPS": [
                {"name": "DDA", "class": "Arcanist", "report_code": "A", "fight_id": 1},
                {"name": "DDB", "class": "Arcanist", "report_code": "A", "fight_id": 1},
                {"name": "DDC", "class": "Arcanist", "report_code": "B", "fight_id": 2},
            ],
            "Healer": [
                {"name": "HealA", "class": "Warden", "report_code": "A", "fight_id": 1},
                {"name": "HealB", "class": "Warden", "report_code": "B", "fight_id": 2},
            ],
            "Tank": [
                {"name": "TankA", "class": "Dragonknight", "report_code": "A", "fight_id": 1},
                {"name": "TankB", "class": "Necromancer", "report_code": "B", "fight_id": 2},
            ],
        }

    def get_trial_zones(self):
        return [
            {
                "id": 1,
                "name": "Sunspire",
                "encounters": [{"id": 99, "name": "Nahviintaas"}],
            }
        ]

    def get_role_rankings(self, encounter_id, role, metric, limit=5):
        assert encounter_id == 99
        self.ranking_calls.append((role, metric, limit))
        return self.rankings[role][:limit]

    def get_fight(self, report_code, fight_id):
        return {"startTime": 0, "endTime": 10_000}

    def get_report_player_summary(self, report_code, fight_id, start, end):
        self.summary_calls.append((report_code, fight_id))

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
                },
                {
                    "name": "NotRankedDD",
                    "type": "Arcanist",
                    "combatantInfo": {
                        "gear": [{"setName": "Random Team Set"}]
                    },
                },
            ],
        }


def test_trending_aggregates_top_individual_players_by_role():
    client = _TrendingClient()
    report = EsoLogsTrendingService(client).analyze_encounter(
        zone_id=1,
        zone_name="Sunspire",
        encounter_id=99,
        encounter_name="Nahviintaas",
        player_limit=3,
    )

    assert client.ranking_calls == [
        ("DPS", "dps", 3),
        ("Healer", "hps", 3),
        ("Tank", "dps", 3),
    ]
    assert report.ranked_players_analyzed == 7
    assert report.ranked_players_skipped == 0
    assert report.players_analyzed == 7

    # Seven ranked players came from only two reports. Their full team summaries are
    # fetched once each, then only the ranked identities are retained.
    assert client.summary_calls == [("A", 1), ("B", 2)]

    dd = report.role_summaries["dps"]
    assert dd.player_count == 3
    assert [(row.name, row.count) for row in dd.gear_sets[:3]] == [
        ("Coral Riptide", 3),
        ("Deadly Strike", 2),
        ("Ansuul's Torment", 1),
    ]
    assert all(row.name != "Random Team Set" for row in dd.gear_sets)
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
        player_limit=1,
    )

    tank = report.role_summaries["tank"]
    pearlescent = next(row for row in tank.gear_sets if row.name == "Pearlescent Ward")
    assert pearlescent.count == 1
    assert pearlescent.player_count == 1
    assert pearlescent.percent == 100.0


def test_trending_skips_ranked_identity_that_cannot_be_matched_exactly():
    client = _TrendingClient()
    client.rankings["DPS"] = [
        {"name": "MissingDD", "class": "Arcanist", "report_code": "B", "fight_id": 2}
    ]

    report = EsoLogsTrendingService(client).analyze_encounter(
        zone_id=1,
        zone_name="Sunspire",
        encounter_id=99,
        encounter_name="Nahviintaas",
        player_limit=5,
    )

    assert report.ranked_players_skipped == 1
    assert report.role_summaries["dps"].player_count == 0
    assert all(
        player.Name != "NotRankedDD"
        for summary in report.role_summaries.values()
        for player in summary.sample_players
    )


def test_trending_fails_when_no_ranked_player_is_usable():
    class _BrokenClient(_TrendingClient):
        def get_report_player_summary(self, report_code, fight_id, start, end):
            raise EsoLogsApiError("private")

    try:
        EsoLogsTrendingService(_BrokenClient()).analyze_encounter(
            zone_id=1,
            zone_name="Sunspire",
            encounter_id=99,
            encounter_name="Nahviintaas",
            player_limit=3,
        )
    except EsoLogsApiError as exc:
        assert "Could not load usable top-ranked players" in str(exc)
    else:
        raise AssertionError("Expected EsoLogsApiError")
