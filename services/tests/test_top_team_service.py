from services.top_team_service import TopTeamService


def test_top_team_extracts_report_and_fight_from_nested_ranking():
    ranking = {"report": {"code": "ABC123", "fightID": 17}}

    assert TopTeamService._ranking_report_fight(ranking) == ("ABC123", 17)


def test_top_team_extracts_and_deduplicates_set_names():
    actor = {
        "combatantInfo": {
            "gear": [
                {"setName": "Pearlescent Ward"},
                {"setName": "Pearlescent Ward"},
                {"set": {"name": "Turning Tide"}},
                {"set": "Nazaray"},
                {"name": "Ordinary Non-set Item"},
            ]
        }
    }

    assert TopTeamService._gear_sets(actor) == [
        "Pearlescent Ward",
        "Turning Tide",
        "Nazaray",
    ]


def test_top_team_accepts_rankings_json_scalar():
    payload = '{"rankings":[{"report":{"code":"XYZ","fightID":4}}]}'

    assert TopTeamService._first_ranking(payload) == {
        "report": {"code": "XYZ", "fightID": 4}
    }


class _FakeClient:
    def __init__(self):
        self.query_calls = []
        self.aura_calls = []

    def _query(self, query, variables):
        self.query_calls.append((query, variables))
        if "fightRankings" in query:
            return {
                "worldData": {
                    "encounter": {
                        "fightRankings": {
                            "rankings": [
                                {"report": {"code": "ABC123", "fightID": 7}}
                            ]
                        }
                    }
                }
            }
        return {
            "reportData": {
                "report": {
                    "playerDetails": {
                        "tanks": [],
                        "healers": [
                            {
                                "id": 42,
                                "name": "ObservedHealer",
                                "type": "Warden",
                                "combatantInfo": {
                                    "gear": [
                                        {"setName": "Serpent's Disdain"},
                                        {"set": {"name": "Pillager's Profit"}},
                                    ],
                                    "talents": [
                                        {"name": "Combat Prayer"},
                                        {"ability": {"name": "Energy Orb"}},
                                        {"name": "Combat Prayer"},
                                    ],
                                },
                            }
                        ],
                        "dps": [],
                    }
                }
            }
        }

    def get_fight(self, report_code, fight_id):
        assert report_code == "ABC123"
        assert fight_id == 7
        return {"startTime": 1000, "endTime": 11000}

    def get_aura_table(
        self,
        report_code,
        fight_id,
        start_time,
        end_time,
        *,
        data_type,
        hostility_type,
        source_id,
    ):
        self.aura_calls.append(
            (
                report_code,
                fight_id,
                start_time,
                end_time,
                data_type,
                hostility_type,
                source_id,
            )
        )
        return [
            {"name": "Major Resolve", "totalUptime": 9000},
            {"name": "The Ritual", "totalUptime": 9000},
        ]


def test_top_team_initial_fetch_restores_class_and_skills_without_eager_aura_calls():
    client = _FakeClient()
    service = TopTeamService(client)

    result = service.get_top_team(
        zone_id=99,
        zone_name="Dreadsail Reef",
        encounter_id=123,
        encounter_name="Taleria",
    )

    assert result.ReportCode == "ABC123"
    assert result.FightId == 7
    assert len(result.Players) == 1
    player = result.Players[0]
    assert player.Name == "ObservedHealer"
    assert player.Role == "healer"
    assert player.ClassName == "Warden"
    assert player.ActorId == 42
    assert player.GearSets == ["Serpent's Disdain", "Pillager's Profit"]
    assert player.Abilities == ["Combat Prayer", "Energy Orb"]
    assert player.Mundus == ""
    assert client.aura_calls == []


def test_top_team_resolves_mundus_lazily_for_one_selected_player():
    client = _FakeClient()
    service = TopTeamService(client)
    result = service.get_top_team(
        zone_id=99,
        zone_name="Dreadsail Reef",
        encounter_id=123,
        encounter_name="Taleria",
    )
    player = result.Players[0]

    mundus = service.resolve_player_mundus(result, player)

    assert mundus == "The Ritual"
    assert len(client.aura_calls) == 1
    assert client.aura_calls[0][-1] == 42
