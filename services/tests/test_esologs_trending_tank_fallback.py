from services.esologs_client import EsoLogsApiError
from services.esologs_trending_service import EsoLogsTrendingService


class _TankFallbackClient:
    def __init__(self):
        self.calls = []

    def get_trial_zones(self):
        return []

    def _query(self, query, variables):
        self.calls.append((query, dict(variables)))
        metric = variables["metric"]
        class_name = variables.get("className")
        spec_name = variables.get("specName")

        if metric == "dps" and class_name == "Tanks":
            return {
                "worldData": {
                    "encounter": {
                        "characterRankings": {
                            "rankings": [
                                {
                                    "name": "TankA",
                                    "class": "Dragonknight",
                                    "report": {"code": "A", "fightID": 1},
                                }
                            ]
                        }
                    }
                }
            }

        if metric == "tankcombineddps":
            raise EsoLogsApiError("unsupported tank metric")

        if metric == "dps" and spec_name in {"Tank", "tank"}:
            raise EsoLogsApiError("spec filter unavailable")

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
            "dps": [],
        }


def test_trending_prefers_live_tanks_class_damage_rankings():
    client = _TankFallbackClient()

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
    assert tank.gear_sets[0].name == "Pearlescent Ward"

    tank_queries = [variables for _, variables in client.calls if variables["metric"] == "dps"]
    assert any(
        row.get("className") == "Tanks" and row.get("specName") is None
        for row in tank_queries
    )


def test_trending_tank_rankings_keep_legacy_fallbacks_after_class_filter_failure():
    class _LegacyClient(_TankFallbackClient):
        def _query(self, query, variables):
            self.calls.append((query, dict(variables)))
            metric = variables["metric"]
            class_name = variables.get("className")
            spec_name = variables.get("specName")

            if metric == "dps" and class_name == "Tanks":
                raise EsoLogsApiError("class filter unavailable")
            if metric == "tankcombineddps":
                raise EsoLogsApiError("combined metric unavailable")
            if metric == "dps" and spec_name == "Tank":
                return {
                    "worldData": {
                        "encounter": {
                            "characterRankings": {
                                "rankings": [
                                    {
                                        "name": "TankA",
                                        "class": "Dragonknight",
                                        "report": {"code": "A", "fightID": 1},
                                    }
                                ]
                            }
                        }
                    }
                }
            return {"worldData": {"encounter": {"characterRankings": {"rankings": []}}}}

    client = _LegacyClient()
    report = EsoLogsTrendingService(client).analyze_encounter(
        zone_id=1,
        zone_name="Sunspire",
        encounter_id=99,
        encounter_name="Nahviintaas",
        player_limit=5,
    )

    assert report.role_summaries["tank"].player_count == 1
    assert any(row[1].get("className") == "Tanks" for row in client.calls)
    assert any(row[1]["metric"] == "tankcombineddps" for row in client.calls)
    assert any(row[1].get("specName") == "Tank" for row in client.calls)
