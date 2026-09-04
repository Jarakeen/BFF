from types import SimpleNamespace

from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_observed_templates import (
    ObservedTeamTemplateStore,
    ObservedTemplateObjectiveEvaluator,
    observed_template_candidates,
)
from services.team_prescription_pipeline import (
    run_automatic_team_prescription_candidate_pipeline,
)
from services.team_prescription_slot_constraints import PrescribedSlotBuildConstraint


def _store(tmp_path):
    return ObservedTeamTemplateStore(
        tmp_path / "team_prescription_observed_templates.json"
    )


def _result():
    return SimpleNamespace(
        TrialName="Dreadsail Reef",
        EncounterName="Taleria",
        ReportCode="ABC123",
        FightId=7,
    )


def _player():
    return SimpleNamespace(
        Name="ObservedHealer",
        Role="healer",
        EsoClass="Warden",
        GearSets=["Serpent's Disdain", "Pillager's Profit"],
        Skills=["Combat Prayer", "Energy Orb", "Budding Seeds"],
        Mundus="",
    )


def _roster():
    return PrescribedRoster(
        name="Observed Template Test",
        goal="Hurricane Herald",
        scope=TeamPrescriptionScope(
            dimensions=(
                PrescriptionDimension.CLASS,
                PrescriptionDimension.BUILD,
                PrescriptionDimension.GEAR,
                PrescriptionDimension.SKILLS,
                PrescriptionDimension.MUNDUS,
            )
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="Healer",
                unresolved=("Healer 1: requires evidence",),
            ),
        ),
        unresolved=("Healer 1: requires evidence",),
    )


def test_add_top_team_player_persists_partial_observation_idempotently(tmp_path) -> None:
    store = _store(tmp_path)

    first = store.add_top_team_player(
        result=_result(),
        player=_player(),
        game_update="U50",
        retrieved_at="2026-09-04T19:00:00+00:00",
    )
    second = store.add_top_team_player(
        result=_result(),
        player=_player(),
        game_update="U50",
        retrieved_at="2026-09-04T20:00:00+00:00",
    )

    snapshot = store.load()
    assert first.template_id == second.template_id
    assert len(snapshot.templates) == 1
    saved = snapshot.templates[0]
    assert saved.eso_class == "Warden"
    assert saved.role == "Healer"
    assert saved.gear_sets == ("Serpent's Disdain", "Pillager's Profit")
    assert saved.skills == ("Combat Prayer", "Energy Orb", "Budding Seeds")
    assert "gear slot placement" in saved.unknown_fields
    assert "champion points" in saved.unknown_fields
    assert "mundus" in saved.unknown_fields


def test_observed_candidate_preserves_sets_as_metadata_not_fake_gear_slots(tmp_path) -> None:
    store = _store(tmp_path)
    store.add_top_team_player(
        result=_result(),
        player=_player(),
        game_update="U50",
        retrieved_at="2026-09-04T19:00:00+00:00",
    )

    candidate = observed_template_candidates(store.load())[0]

    assert not candidate.has_complete_build_snapshot
    assert candidate.candidate_build.EsoClass == "Warden"
    assert candidate.candidate_build.Role == "Healer"
    assert all(not slot.get("Set") for slot in candidate.candidate_build.Armor.values())
    assert candidate.candidate_metadata["observed_gear_sets"] == [
        "Serpent's Disdain",
        "Pillager's Profit",
    ]
    assert candidate.candidate_metadata["observed_skills"] == [
        "Combat Prayer",
        "Energy Orb",
        "Budding Seeds",
    ]


def test_required_set_can_be_satisfied_by_exact_observed_metadata(tmp_path) -> None:
    store = _store(tmp_path)
    store.add_top_team_player(
        result=_result(),
        player=_player(),
        game_update="U50",
        retrieved_at="2026-09-04T19:00:00+00:00",
    )
    candidate = observed_template_candidates(store.load())[0]
    constraint = PrescribedSlotBuildConstraint(
        slot_name="Healer 1",
        required_class="Warden",
        required_gear_sets=("Serpent's Disdain",),
    )

    assert constraint.matches_candidate(
        candidate.candidate_build,
        candidate.candidate_metadata,
    )


def test_partial_observed_template_can_be_prescribed_but_not_saved_as_complete_build(tmp_path) -> None:
    store = _store(tmp_path)
    store.add_top_team_player(
        result=_result(),
        player=_player(),
        game_update="U50",
        retrieved_at="2026-09-04T19:00:00+00:00",
        source_score=123.0,
    )
    snapshot = store.load()

    result = run_automatic_team_prescription_candidate_pipeline(
        roster=_roster(),
        candidates=observed_template_candidates(snapshot),
        evaluate_objective=ObservedTemplateObjectiveEvaluator(snapshot),
        build_constraints_by_slot={
            "Healer 1": PrescribedSlotBuildConstraint(
                slot_name="Healer 1",
                required_class="Warden",
                required_gear_sets=("Serpent's Disdain",),
            )
        },
    )

    assignment = result.final_roster.assignments[0]
    assert assignment.player_name is None
    assert assignment.prescribed_build is None
    assert assignment.source_build_name == "Warden Healer — Taleria"
    assert assignment.change_for(PrescriptionDimension.CLASS).prescribed_value == "Warden"
    assert "Serpent's Disdain" in assignment.change_for(
        PrescriptionDimension.GEAR
    ).prescribed_value
    assert "Combat Prayer" in assignment.change_for(
        PrescriptionDimension.SKILLS
    ).prescribed_value
    assert any("gear slot placement" in row for row in assignment.unresolved)
    assert any("gear slot placement" in row for row in result.final_roster.unresolved)


def test_observed_template_score_is_explicitly_not_canonical_combat_math(tmp_path) -> None:
    store = _store(tmp_path)
    store.add_top_team_player(
        result=_result(),
        player=_player(),
        game_update="U50",
        retrieved_at="2026-09-04T19:00:00+00:00",
        source_score=321.0,
    )
    snapshot = store.load()
    candidate = observed_template_candidates(snapshot)[0]

    measurement = ObservedTemplateObjectiveEvaluator(snapshot)(candidate, "Healer 1")

    assert measurement.value == 321.0
    assert measurement.metric_name == "observed performance-template score"
    assert measurement.is_rankable
    assert any("not canonical damage/HPS/tank math" in row for row in measurement.evidence)
