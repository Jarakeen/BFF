from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.team_prescription_observed_templates import ObservedTeamTemplateStore
from services.top_team_template_intake import (
    OBSERVED_TEAM_TEMPLATE_FILENAME,
    TopTeamTemplateIntake,
)


class _FakeTopTeamService:
    def __init__(self, resolved_mundus: str = "The Ritual"):
        self.resolved_mundus = resolved_mundus
        self.mundus_calls = 0

    def resolve_player_mundus(self, result, player):
        self.mundus_calls += 1
        assert result.ReportCode == "ABC123"
        assert result.FightId == 7
        assert player.ActorId == 42
        return self.resolved_mundus


def _result() -> TopTeamResult:
    return TopTeamResult(
        TrialName="Dreadsail Reef",
        EncounterName="Taleria",
        ReportCode="ABC123",
        FightId=7,
    )


def _player(*, mundus: str = "") -> TopTeamPlayer:
    return TopTeamPlayer(
        Name="ObservedHealer",
        Role="healer",
        GearSets=["Serpent's Disdain", "Pillager's Profit"],
        ClassName="Warden",
        Abilities=["Combat Prayer", "Energy Orb"],
        Mundus=mundus,
        ActorId=42,
    )


def _intake(tmp_path):
    store = ObservedTeamTemplateStore(
        tmp_path / "team_prescription_observed_templates.json"
    )
    return TopTeamTemplateIntake(store), store


def test_intake_for_data_dir_owns_standard_observed_template_path(tmp_path) -> None:
    intake = TopTeamTemplateIntake.for_data_dir(tmp_path)

    assert intake.store.path == tmp_path / OBSERVED_TEAM_TEMPLATE_FILENAME


def test_intake_can_save_observed_setup_without_requesting_mundus(tmp_path) -> None:
    intake, store = _intake(tmp_path)
    service = _FakeTopTeamService()
    player = _player()

    outcome = intake.add_player(
        top_team_service=service,
        result=_result(),
        player=player,
        game_update="U50",
        retrieved_at="2026-09-04T20:00:00+00:00",
        include_mundus=False,
    )

    assert service.mundus_calls == 0
    assert not outcome.mundus_lookup_requested
    assert not outcome.mundus_resolved
    assert outcome.template.mundus == ""
    assert "mundus" in outcome.template.unknown_fields
    assert player.Mundus == ""
    assert store.load().templates == (outcome.template,)


def test_intake_resolves_only_selected_players_mundus_and_preserves_original_result(tmp_path) -> None:
    intake, store = _intake(tmp_path)
    service = _FakeTopTeamService("The Ritual")
    player = _player()
    result = _result()
    result.Players.append(player)

    outcome = intake.add_player(
        top_team_service=service,
        result=result,
        player=player,
        game_update="U50",
        retrieved_at="2026-09-04T20:00:00+00:00",
        include_mundus=True,
    )

    assert service.mundus_calls == 1
    assert outcome.mundus_lookup_requested
    assert outcome.mundus_resolved
    assert outcome.template.mundus == "The Ritual"
    assert "mundus" not in outcome.template.unknown_fields
    assert player.Mundus == ""
    assert result.Players[0].Mundus == ""
    saved = store.load().templates[0]
    assert saved.source_name == "ESO Logs"
    assert saved.source_url == "https://www.esologs.com/reports/ABC123"
    assert saved.report_code == "ABC123"
    assert saved.fight_id == 7
    assert saved.trial_name == "Dreadsail Reef"
    assert saved.encounter_name == "Taleria"
    assert saved.game_update == "U50"


def test_intake_does_not_repeat_mundus_lookup_when_player_already_has_it(tmp_path) -> None:
    intake, _store = _intake(tmp_path)
    service = _FakeTopTeamService("The Thief")

    outcome = intake.add_player(
        top_team_service=service,
        result=_result(),
        player=_player(mundus="The Ritual"),
        game_update="U50",
        retrieved_at="2026-09-04T20:00:00+00:00",
        include_mundus=True,
    )

    assert service.mundus_calls == 0
    assert not outcome.mundus_lookup_requested
    assert outcome.mundus_resolved
    assert outcome.template.mundus == "The Ritual"


def test_intake_keeps_mundus_unresolved_when_lazy_lookup_returns_no_evidence(tmp_path) -> None:
    intake, _store = _intake(tmp_path)
    service = _FakeTopTeamService("")

    outcome = intake.add_player(
        top_team_service=service,
        result=_result(),
        player=_player(),
        game_update="U50",
        retrieved_at="2026-09-04T20:00:00+00:00",
        include_mundus=True,
    )

    assert service.mundus_calls == 1
    assert outcome.mundus_lookup_requested
    assert not outcome.mundus_resolved
    assert outcome.template.mundus == ""
    assert "mundus" in outcome.template.unknown_fields
