from services.esologs_client import EsoLogsApiError
from services.top_team_service import TopTeamService


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


class _FakeClient:
    def __init__(self):
        self.query_calls = []
        self.aura_calls = []
        self.trial_zone_calls = 0
        self.report_candidates = [("ABC123", 7)]
        self.summary_calls = []

    def get_trial_zones(self):
        self.trial_zone_calls += 1
        return [
            {
                "id": 15,
                "name": "Dreadsail Reef",
                "encounters": [{"id": 123, "name": "Taleria"}],
            }
        ]

    def get_top_reports_for_encounter(self, encounter_id, limit=10):
        assert encounter_id == 123
        return self.report_candidates[:limit]

    def get_fight(self, report_code, fight_id):
        return {"startTime": 1000, "endTime": 11000}

    def get_report_player_summary(
        self, report_code, fight_id, start_time, end_time
    ):
        self.summary_calls.append((report_code, fight_id))
        return {
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


def test_top_team_trial_picker_delegates_to_clients_trial_only_filter():
    client = _FakeClient()
    service = TopTeamService(client)

    trials = service.list_trials()

    assert trials == [
        {
            "id": 15,
            "name": "Dreadsail Reef",
            "encounters": [{"id": 123, "name": "Taleria"}],
        }
    ]
    assert client.trial_zone_calls == 1
    assert client.query_calls == []


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


def test_top_team_falls_through_private_report_without_mixing_teams():
    class _FallbackClient(_FakeClient):
        def __init__(self):
            super().__init__()
            self.report_candidates = [("PRIVATE", 1), ("ABC123", 7)]

        def get_report_player_summary(
            self, report_code, fight_id, start_time, end_time
        ):
            if report_code == "PRIVATE":
                self.summary_calls.append((report_code, fight_id))
                raise EsoLogsApiError("Report is private")
            return super().get_report_player_summary(
                report_code, fight_id, start_time, end_time
            )

    client = _FallbackClient()
    result = TopTeamService(client).get_top_team(
        zone_id=99,
        zone_name="Dreadsail Reef",
        encounter_id=123,
        encounter_name="Taleria",
    )

    assert result.ReportCode == "ABC123"
    assert [player.Name for player in result.Players] == ["ObservedHealer"]
    assert client.summary_calls == [
        ("PRIVATE", 1),
        ("ABC123", 7),
    ]


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
