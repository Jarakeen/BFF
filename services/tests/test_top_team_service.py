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
