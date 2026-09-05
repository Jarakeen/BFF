from __future__ import annotations

import json

from services.comp_builder_authoritative_prescription import (
    CompBuilderAuthoritativePrescriptionService,
)
from services.comp_builder_build_candidates import CompBuilderBuildCandidateService


def _saved_build() -> dict:
    return {
        "Name": "Magrat",
        "BuildName": "DF Healer",
        "EsoClass": "Warden",
        "Role": "Healer",
        "Race": "Breton",
        "Mundus": "The Ritual",
        "Armor": {
            "Chest": {"Set": "Spell Power Cure"},
            "Legs": {"Set": "Pillager's Profit"},
        },
        "FrontBarSkills": ["Combat Prayer", "Energy Orb", "", "", "", ""],
        "BackBarSkills": ["Budding Seeds", "", "", "", "", ""],
    }


def _template(*, complete: bool) -> dict:
    return {
        "template_id": "warden-healer-reference",
        "name": "Reference Warden Healer",
        "source_name": "BTV Tools",
        "source_url": "https://www.btvtools.com/",
        "retrieved_at": "2026-09-05",
        "base_score": 10,
        "slot_scores": {"Healer 2": 100},
        "goal_scores": {"Godslayer": 20},
        "complete_build": complete,
        "unresolved": ([] if complete else ["race unresolved", "CP unresolved"]),
        "build": {
            "Name": "Published Reference Template",
            "BuildName": "Reference Warden Healer",
            "EsoClass": "Warden",
            "Role": "Healer",
            "Mundus": "The Ritual",
            "Armor": {"Chest": {"Set": "Roaring Opportunist"}},
            "FrontBarSkills": ["Combat Prayer", "", "", "", "", ""],
        },
    }


def _write_sources(tmp_path, *, complete_template: bool) -> None:
    (tmp_path / "builds.json").write_text(
        json.dumps({"Members": [_saved_build()]}),
        encoding="utf-8",
    )
    (tmp_path / "characters.json").write_text(
        json.dumps({"characters": []}),
        encoding="utf-8",
    )
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_version": "test-u50",
                "game_update": "Update 50",
                "templates": [_template(complete=complete_template)],
            }
        ),
        encoding="utf-8",
    )


def test_materialization_preserves_exact_saved_optimizer_choice(tmp_path) -> None:
    _write_sources(tmp_path, complete_template=False)
    candidates = CompBuilderBuildCandidateService(tmp_path).candidates_for_chair(
        goal="Godslayer",
        slot_name="Healer 1",
        role="Healer",
        preferred_class="Warden",
    )
    saved = next(candidate for candidate in candidates if candidate.source_kind == "saved_build")

    roster = CompBuilderAuthoritativePrescriptionService(tmp_path).materialize(
        name="Godslayer Team",
        goal="Godslayer",
        slots=(("Healer 1", "Healer"),),
        candidates_by_slot={"Healer 1": saved},
    )

    assignment = roster.assignments[0]
    assert assignment.player_name == "Magrat"
    assert assignment.source_build_name == "DF Healer"
    assert assignment.prescribed_build is not None
    assert assignment.prescribed_build.BuildName == "DF Healer"
    assert assignment.prescribed_build.Race == "Breton"
    assert any("authoritative" in value for value in roster.assumptions)


def test_complete_reference_materializes_without_becoming_fake_player(tmp_path) -> None:
    _write_sources(tmp_path, complete_template=True)
    candidates = CompBuilderBuildCandidateService(tmp_path).candidates_for_chair(
        goal="Godslayer",
        slot_name="Healer 2",
        role="Healer",
        preferred_class="Warden",
    )
    reference = next(
        candidate for candidate in candidates if candidate.source_kind == "reference_template"
    )

    roster = CompBuilderAuthoritativePrescriptionService(tmp_path).materialize(
        name="Godslayer Team",
        goal="Godslayer",
        slots=(("Healer 2", "Healer"),),
        candidates_by_slot={"Healer 2": reference},
    )

    assignment = roster.assignments[0]
    assert assignment.player_name is None
    assert assignment.source_build_name == "Reference Warden Healer"
    assert assignment.prescribed_build is not None
    assert assignment.prescribed_build.BuildName == "Reference Warden Healer"
    assert roster.unresolved == ()


def test_partial_reference_remains_partial_after_authoritative_selection(tmp_path) -> None:
    _write_sources(tmp_path, complete_template=False)
    candidates = CompBuilderBuildCandidateService(tmp_path).candidates_for_chair(
        goal="Godslayer",
        slot_name="Healer 2",
        role="Healer",
        preferred_class="Warden",
    )
    reference = next(
        candidate for candidate in candidates if candidate.source_kind == "reference_template"
    )

    roster = CompBuilderAuthoritativePrescriptionService(tmp_path).materialize(
        name="Godslayer Team",
        goal="Godslayer",
        slots=(("Healer 2", "Healer"),),
        candidates_by_slot={"Healer 2": reference},
    )

    assignment = roster.assignments[0]
    assert assignment.player_name is None
    assert assignment.prescribed_build is None
    assert assignment.source_build_name == "Reference Warden Healer"
    assert {change.dimension.value for change in assignment.changes} >= {
        "class",
        "build",
        "gear",
        "skills",
        "mundus",
    }
    assert "race unresolved" in assignment.unresolved
    assert any("partial reference evidence" in value for value in roster.unresolved)


def test_unselected_chair_stays_explicitly_unresolved(tmp_path) -> None:
    _write_sources(tmp_path, complete_template=False)

    roster = CompBuilderAuthoritativePrescriptionService(tmp_path).materialize(
        name="Godslayer Team",
        goal="Godslayer",
        slots=(("DD 1", "DD"),),
        candidates_by_slot={},
    )

    assert roster.assignments[0].prescribed_build is None
    assert roster.assignments[0].player_name is None
    assert roster.unresolved == (
        "DD 1: no authoritative Comp Maker candidate was selected",
    )
