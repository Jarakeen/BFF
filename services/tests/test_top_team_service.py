from __future__ import annotations

import pytest

from services.esologs_client import EsoLogsApiError
from services.top_team_service import TopTeamService


# --------------------------------------------------
# actor-parsing helpers (unchanged by the query-layer swap)
# --------------------------------------------------


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


def test_top_team_reads_class_name_from_type_field():
    assert TopTeamService._class_name({"type": "Templar"}) == "Templar"
    assert TopTeamService._class_name({"class": "Warden"}) == "Warden"
    assert TopTeamService._class_name({}) == ""


def test_top_team_extracts_and_deduplicates_abilities():
    actor = {
        "combatantInfo": {
            "talents": [
                {"name": "Combat Prayer"},
                {"name": "Combat Prayer"},
                {"ability": "Efficient Purge"},
                "Radiating Regeneration",
            ]
        }
    }

    assert TopTeamService._abilities(actor) == [
        "Combat Prayer",
        "Efficient Purge",
        "Radiating Regeneration",
    ]


def test_top_team_abilities_handles_missing_talents_gracefully():
    assert TopTeamService._abilities({}) == []
    assert TopTeamService._abilities({"talents": "not-a-list"}) == []


# --------------------------------------------------
# get_top_team orchestration (per-role rankings)
# --------------------------------------------------


class _FakeClient:
    """
    Stands in for EsoLogsClient at the method boundary TopTeamService
    now actually calls (get_trial_zones / get_role_rankings /
    get_fight / get_report_player_summary).
    """

    def __init__(self, role_rankings=None, player_details_by_code=None, fail_roles=None):
        # role_rankings: {"Tank": [...], "Healer": [...], "DPS": [...]}
        self.role_rankings = role_rankings or {}
        self.player_details_by_code = player_details_by_code or {}
        self.fail_roles = fail_roles or {}
        self.role_ranking_calls = []
        self.player_query_calls = []

    def get_trial_zones(self):
        return [{"id": 15, "name": "Rockgrove", "encounters": [{"id": 63, "name": "Oaxiltso"}]}]

    def get_role_rankings(self, encounter_id, role, metric, limit=5):
        self.role_ranking_calls.append(role)
        if role in self.fail_roles:
            raise self.fail_roles[role]
        return self.role_rankings.get(role, [])[:limit]

    def get_fight(self, report_code, fight_id):
        return {"startTime": 0.0, "endTime": 1000.0}

    def get_report_player_summary(self, report_code, fight_id, start_time, end_time):
        self.player_query_calls.append((report_code, fight_id))
        return self.player_details_by_code.get(
            (report_code, fight_id), {"tanks": [], "healers": [], "dps": []}
        )


def _entry(name, report_code, fight_id, class_name="Templar"):
    return {"name": name, "class": class_name, "report_code": report_code, "fight_id": fight_id}


def test_get_top_team_pulls_top_players_per_role_from_their_own_reports():

    client = _FakeClient(
        role_rankings={
            "Tank": [_entry("TankyMcTank", "R1", 1)],
            "Healer": [_entry("HealBot", "R2", 1)],
            "DPS": [_entry("BigNumbers", "R3", 1)],
        },
        player_details_by_code={
            ("R1", 1): {"tanks": [{"name": "TankyMcTank", "type": "Dragonknight", "combatantInfo": {"gear": []}}], "healers": [], "dps": []},
            ("R2", 1): {"tanks": [], "healers": [{"name": "HealBot", "type": "Warden", "combatantInfo": {"gear": []}}], "dps": []},
            ("R3", 1): {"tanks": [], "healers": [], "dps": [{"name": "BigNumbers", "type": "Nightblade", "combatantInfo": {"gear": []}}]},
        },
    )

    service = TopTeamService(client)

    result = service.get_top_team(
        zone_id=15, zone_name="Rockgrove", encounter_id=63, encounter_name="Oaxiltso"
    )

    names_by_role = {p.Role: p.Name for p in result.Players}

    assert names_by_role == {"tank": "TankyMcTank", "healer": "HealBot", "dps": "BigNumbers"}
    assert result.SourceReportCount == 3
    assert sorted(client.role_ranking_calls) == ["DPS", "Healer", "Tank"]


def test_get_top_team_dedupes_report_fetches_when_players_share_a_log():
    """
    Two top-ranked players from different roles in the SAME log must
    only cost one gear-details fetch, not one per player.
    """

    client = _FakeClient(
        role_rankings={
            "Tank": [_entry("TankyMcTank", "SHARED", 1)],
            "Healer": [_entry("HealBot", "SHARED", 1)],
            "DPS": [],
        },
        player_details_by_code={
            ("SHARED", 1): {
                "tanks": [{"name": "TankyMcTank", "combatantInfo": {"gear": []}}],
                "healers": [{"name": "HealBot", "combatantInfo": {"gear": []}}],
                "dps": [],
            },
        },
        fail_roles={"DPS": EsoLogsApiError("No ranked DPS parses were found for this encounter.")},
    )

    service = TopTeamService(client)

    result = service.get_top_team(
        zone_id=15, zone_name="Rockgrove", encounter_id=63, encounter_name="Oaxiltso"
    )

    assert client.player_query_calls == [("SHARED", 1)]  # fetched once, not twice
    assert len(result.Players) == 2
    assert result.SourceReportCount == 1


def test_get_top_team_dedupes_same_player_ranking_in_role_twice():

    client = _FakeClient(
        role_rankings={
            "Tank": [_entry("TankyMcTank", "R1", 1), _entry("TankyMcTank", "R2", 1)],
            "Healer": [],
            "DPS": [],
        },
        player_details_by_code={
            ("R1", 1): {"tanks": [{"name": "TankyMcTank", "combatantInfo": {"gear": ["A"]}}], "healers": [], "dps": []},
            ("R2", 1): {"tanks": [{"name": "TankyMcTank", "combatantInfo": {"gear": ["B"]}}], "healers": [], "dps": []},
        },
        fail_roles={
            "Healer": EsoLogsApiError("no healers"),
            "DPS": EsoLogsApiError("no dps"),
        },
    )

    service = TopTeamService(client)

    result = service.get_top_team(
        zone_id=15, zone_name="Rockgrove", encounter_id=63, encounter_name="Oaxiltso"
    )

    assert len(result.Players) == 1  # kept only the first (highest-ranked) occurrence


def test_get_top_team_continues_when_one_role_fails_entirely():

    client = _FakeClient(
        role_rankings={
            "Tank": [_entry("TankyMcTank", "R1", 1)],
            "Healer": [],
            "DPS": [],
        },
        player_details_by_code={
            ("R1", 1): {"tanks": [{"name": "TankyMcTank", "combatantInfo": {"gear": []}}], "healers": [], "dps": []},
        },
        fail_roles={
            "Healer": EsoLogsApiError("No ranked Healer parses were found for this encounter."),
            "DPS": EsoLogsApiError("No ranked DPS parses were found for this encounter."),
        },
    )

    service = TopTeamService(client)

    result = service.get_top_team(
        zone_id=15, zone_name="Rockgrove", encounter_id=63, encounter_name="Oaxiltso"
    )

    assert [p.Role for p in result.Players] == ["tank"]


def test_get_top_team_raises_when_every_role_fails():

    client = _FakeClient(
        fail_roles={
            "Tank": EsoLogsApiError("no tanks"),
            "Healer": EsoLogsApiError("no healers"),
            "DPS": EsoLogsApiError("no dps"),
        },
    )

    service = TopTeamService(client)

    with pytest.raises(EsoLogsApiError, match="Could not build a top-players list"):
        service.get_top_team(
            zone_id=15, zone_name="Rockgrove", encounter_id=63, encounter_name="Oaxiltso"
        )


def test_get_top_team_skips_a_player_missing_from_the_fetched_report():
    """
    Defensive case: the ranking entry names a player, but that exact
    name isn't found in the role bucket of the report's playerDetails
    (name mismatch, anonymized entry, etc.) -- skip that one player
    rather than crashing or fabricating a blank entry.
    """

    client = _FakeClient(
        role_rankings={
            "Tank": [_entry("Ghost", "R1", 1)],
            "Healer": [],
            "DPS": [],
        },
        player_details_by_code={
            ("R1", 1): {"tanks": [{"name": "SomeoneElse", "combatantInfo": {"gear": []}}], "healers": [], "dps": []},
        },
        fail_roles={
            "Healer": EsoLogsApiError("no healers"),
            "DPS": EsoLogsApiError("no dps"),
        },
    )

    service = TopTeamService(client)

    with pytest.raises(EsoLogsApiError, match="Could not build a top-players list"):
        service.get_top_team(
            zone_id=15, zone_name="Rockgrove", encounter_id=63, encounter_name="Oaxiltso"
        )
