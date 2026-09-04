import json

from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_observed_templates import ObservedTeamTemplateStore
from services.team_prescription_template_sources import apply_team_template_sources


class _Result:
    TrialName = "Dreadsail Reef"
    EncounterName = "Taleria"
    ReportCode = "ABC123"
    FightId = 7


class _Player:
    Name = "ObservedHealer"
    Role = "healer"
    EsoClass = "Warden"
    GearSets = ["Serpent's Disdain", "Pillager's Profit"]
    Skills = ["Combat Prayer", "Energy Orb"]
    Mundus = ""


def _roster():
    return PrescribedRoster(
        name="Template Sources",
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


def _add_observed(tmp_path, *, score: float = 123.0) -> None:
    ObservedTeamTemplateStore(
        tmp_path / "team_prescription_observed_templates.json"
    ).add_top_team_player(
        result=_Result(),
        player=_Player(),
        game_update="U50",
        retrieved_at="2026-09-04T19:00:00+00:00",
        source_score=score,
    )


def test_observed_templates_fill_open_slot_when_no_complete_catalog_exists(tmp_path) -> None:
    _add_observed(tmp_path)

    result = apply_team_template_sources(
        roster=_roster(),
        goal="Hurricane Herald",
        data_dir=tmp_path,
    )

    assignment = result.final_roster.assignments[0]
    assert result.published_template_count == 0
    assert result.observed_template_count == 1
    assert result.applied_count == 1
    assert assignment.source_build_name == "Warden Healer — Taleria"
    assert assignment.prescribed_build is None
    assert assignment.change_for(PrescriptionDimension.GEAR) is not None


def test_complete_published_template_fills_slot_before_partial_observed_template(tmp_path) -> None:
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_version": "u50-test",
                "game_update": "U50",
                "templates": [
                    {
                        "template_id": "published:warden-healer",
                        "name": "Published Warden Healer",
                        "source_name": "Curated Test Source",
                        "source_url": "https://example.invalid/template",
                        "retrieved_at": "2026-09-04",
                        "base_score": 200.0,
                        "complete_build": True,
                        "build": {
                            "BuildName": "Published Warden Healer",
                            "EsoClass": "Warden",
                            "Role": "Healer",
                            "FrontBarSkills": ["Combat Prayer"],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _add_observed(tmp_path, score=999.0)

    result = apply_team_template_sources(
        roster=_roster(),
        goal="Hurricane Herald",
        data_dir=tmp_path,
    )

    assignment = result.final_roster.assignments[0]
    assert result.published_template_count == 1
    assert result.observed_template_count == 1
    assert result.applied_count == 1
    assert assignment.source_build_name == "Published Warden Healer"
    assert assignment.prescribed_build is not None


def test_partial_published_template_keeps_priority_over_later_observed_template(tmp_path) -> None:
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_version": "u50-test",
                "game_update": "U50",
                "templates": [
                    {
                        "template_id": "published:partial-healer",
                        "name": "Partial Published Healer",
                        "source_name": "Curated Test Source",
                        "source_url": "https://example.invalid/partial",
                        "retrieved_at": "2026-09-04",
                        "base_score": 200.0,
                        "unresolved": ["exact traits and enchants unresolved"],
                        "build": {
                            "BuildName": "Partial Published Healer",
                            "EsoClass": "Warden",
                            "Role": "Healer",
                            "FrontBarSkills": ["Combat Prayer", "Energy Orb"],
                            "Mundus": "The Ritual",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    # The observed score is deliberately much larger. Source priority, not
    # incomparable numeric score magnitude, decides whether it may replace the
    # already-curated recommendation.
    _add_observed(tmp_path, score=999.0)

    result = apply_team_template_sources(
        roster=_roster(),
        goal="Hurricane Herald",
        data_dir=tmp_path,
    )

    assignment = result.final_roster.assignments[0]
    assert result.published_template_count == 1
    assert result.observed_template_count == 1
    assert result.applied_count == 1
    assert assignment.source_build_name == "Partial Published Healer"
    assert assignment.prescribed_build is None
    assert assignment.change_for(PrescriptionDimension.SKILLS) is not None
    assert assignment.change_for(PrescriptionDimension.MUNDUS).prescribed_value == "The Ritual"
    assert any("exact traits and enchants unresolved" in row for row in assignment.unresolved)
