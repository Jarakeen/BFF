from services.esologs_client import EsoLogsClient


class _RoleRankingClient(EsoLogsClient):
    def __init__(self):
        super().__init__(client_id="id", client_secret="secret")
        self.calls = []

    def _query(self, query: str, variables: dict) -> dict:
        self.calls.append((query, variables))
        return {
            "worldData": {
                "encounter": {
                    "characterRankings": {
                        "rankings": [
                            {
                                "name": "RankedPlayer",
                                "class": "Arcanist",
                                "report": {"code": "ABC123", "fightID": 7},
                            }
                        ]
                    }
                }
            }
        }


def test_role_rankings_queries_individual_role_and_metric():
    client = _RoleRankingClient()

    rows = client.get_role_rankings(99, role="Healer", metric="hps", limit=5)

    assert rows == [
        {
            "name": "RankedPlayer",
            "class": "Arcanist",
            "report_code": "ABC123",
            "fight_id": 7,
        }
    ]
    assert len(client.calls) == 1
    query, variables = client.calls[0]
    assert "characterRankings(role: $role, metric: $metric)" in query
    assert variables == {
        "encounterID": 99,
        "role": "Healer",
        "metric": "hps",
    }
