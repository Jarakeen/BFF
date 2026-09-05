from __future__ import annotations

import json

from services.comp_builder_build_candidates import CompBuilderBuildCandidateService


def _saved_build(name: str, eso_class: str, role: str) -> dict:
    return {
        "Name": "Magrat",
        "BuildName": name,
        "EsoClass": eso_class,
        "Role": role,
        "Mundus": "The Ritual",
        "Armor": {
            "Chest": {"Set": "Spell Power Cure"},
            "Legs": {"Set": "Pillager's Profit"},
        },
        "FrontBarSkills": ["Combat Prayer", "Energy Orb", "", "", "", ""],
        "BackBarSkills": ["Budding Seeds", "", "", "", "", ""],
    }


def _template(name: str, eso_class: str, role: str) -> dict:
    return {
        "template_id": "reference-warden-healer",
        "name": name,
        "source_name": "BTV Tools",
        "source_url": "https://www.btvtools.com/",
        "retrieved_at": "2026-09-04",
        "base_score": 10,
        "slot_scores": {"Healer 1": 100},
        "goal_scores": {"Godslayer": 25},
        "complete_build": False,
        "unresolved": ["gear and skills unresolved"],
        "build": {
            "Name": "Published Reference Template",
            "BuildName": name,
            "EsoClass": eso_class,
            "Role": role,
        },
    }


def test_saved_build_and_reference_template_merge_for_matching_chair(tmp_path) -> None:
    (tmp_path / "builds.json").write_text(
        json.dumps({"Members": [_saved_build("DF Healer", "Warden", "Healer")]}),
        encoding="utf-8",
    )
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_version": "test-u50",
                "game_update": "Update 50",
                "templates": [_template("Reference Warden", "Warden", "Healer")],
            }
        ),
        encoding="utf-8",
    )

    candidates = CompBuilderBuildCandidateService(tmp_path).candidates_for_chair(
        goal="Godslayer",
        slot_name="Healer 1",
        role="Healer",
        preferred_class="Warden",
    )

    assert [candidate.name for candidate in candidates] == ["DF Healer", "Reference Warden"]
    assert candidates[0].source_kind == "saved_build"
    assert "Spell Power Cure" in candidates[0].gear_sets
    assert "Pillager's Profit" in candidates[0].gear_sets
    assert "Combat Prayer" in candidates[0].skills
    assert candidates[1].source_kind == "reference_template"
    assert candidates[1].gear_sets == ()
    assert candidates[1].unresolved == ("gear and skills unresolved",)


def test_observed_overlap_increases_saved_build_relevance(tmp_path) -> None:
    first = _saved_build("Observed Match", "Warden", "Healer")
    second = _saved_build("Other Setup", "Warden", "Healer")
    second["Armor"] = {"Chest": {"Set": "Roaring Opportunist"}}
    second["FrontBarSkills"] = ["Illustrious Healing", "", "", "", "", ""]
    second["BackBarSkills"] = ["", "", "", "", "", ""]
    (tmp_path / "builds.json").write_text(
        json.dumps({"Members": [first, second]}),
        encoding="utf-8",
    )
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_version": "test-u50",
                "game_update": "Update 50",
                "templates": [],
            }
        ),
        encoding="utf-8",
    )

    candidates = CompBuilderBuildCandidateService(tmp_path).candidates_for_chair(
        goal="Godslayer",
        slot_name="Healer 1",
        role="Healer",
        preferred_class="Warden",
        observed_gear_sets=("Spell Power Cure",),
        observed_skills=("Combat Prayer", "Energy Orb"),
    )

    assert candidates[0].name == "Observed Match"
    assert candidates[0].score > candidates[1].score
    assert any("observed gear-set" in reason for reason in candidates[0].score_reasons)
    assert any("observed skill" in reason for reason in candidates[0].score_reasons)


def test_role_and_class_boundaries_exclude_unrelated_saved_builds(tmp_path) -> None:
    (tmp_path / "builds.json").write_text(
        json.dumps(
            {
                "Members": [
                    _saved_build("Warden Healer", "Warden", "Healer"),
                    _saved_build("Warden DD", "Warden", "DD"),
                    _saved_build("Arcanist Healer", "Arcanist", "Healer"),
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_version": "test-u50",
                "game_update": "Update 50",
                "templates": [],
            }
        ),
        encoding="utf-8",
    )

    candidates = CompBuilderBuildCandidateService(tmp_path).candidates_for_chair(
        goal="Godslayer",
        slot_name="Healer 1",
        role="Healer",
        preferred_class="Warden",
    )

    assert [candidate.name for candidate in candidates] == ["Warden Healer"]
