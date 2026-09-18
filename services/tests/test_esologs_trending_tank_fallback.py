from services.esologs_trending_service import EsoLogsTrendingService


class _CoordinatedTankClient:
    def __init__(self):
        self.calls = []

    def get_trial_zones(self):
        return []

    def get_top_reports_for_encounter(self, encounter_id, limit=10):
        self.calls.append(("top_reports", encounter_id, limit))
        return [("A", 1)]

    def _query(self, query, variables):
        self.calls.append(("ranking_query", dict(variables)))
        metric = variables["metric"]
        role_name = variables.get("specName")
        # Healer/DD rankings still use individual ranking evidence.
        if metric in {"dps", "hps"} and role_name is None:
            return {"worldData": {"encounter": {"characterRankings": {"rankings": []}}}}
        return {"worldData": {"encounter": {"characterRankings": {"rankings": []}}}}

    def get_fight(self, report_code, fight_id):
        return {"startTime": 0, "endTime": 10_000}

    def get_report_player_summary(self, report_code, fight_id, start, end):
        return {
            "tanks": [
                {
                    "name": "TankA",
                    "type": "Dragonknight",
                    "combatantInfo": {
                        "gear": [
                            {"setName": "Pearlescent Ward"},
                            {"setName": "Turning Tide"},
                        ]
                    },
                }
            ],
            "healers": [],
            "dps": [
                {
                    "name": "DpsA",
                    "type": "Arcanist",
                    "combatantInfo": {
                        "gear": [
                            {"setName": "Coral Riptide"},
                            {"setName": "Deadly Strike"},
                        ]
                    },
                }
            ],
        }


def test_trending_tank_gear_comes_from_coordinated_tank_bucket():
    client = _CoordinatedTankClient()

    report = EsoLogsTrendingService(client).analyze_encounter(
        zone_id=1,
        zone_name="Sunspire",
        encounter_id=99,
        encounter_name="Nahviintaas",
        player_limit=5,
    )

    tank = report.role_summaries["tank"]
    assert tank.player_count == 1
    assert tank.sample_players[0].Name == "TankA"
    assert tank.sample_players[0].Role == "tank"
    assert [row.name for row in tank.gear_sets] == [
        "Pearlescent Ward",
        "Turning Tide",
    ]
    assert all(
        row.name not in {"Coral Riptide", "Deadly Strike"}
        for row in tank.gear_sets
    )
    assert any(call[0] == "top_reports" for call in client.calls)


def test_trending_tank_path_does_not_use_individual_tank_ranking_queries():
    client = _CoordinatedTankClient()

    EsoLogsTrendingService(client).analyze_encounter(
        zone_id=1,
        zone_name="Sunspire",
        encounter_id=99,
        encounter_name="Nahviintaas",
        player_limit=5,
    )

    ranking_calls = [
        call for call in client.calls
        if call[0] == "ranking_query"
        and call[1].get("metric") in {"tankcombineddps"}
    ]
    assert ranking_calls == []
