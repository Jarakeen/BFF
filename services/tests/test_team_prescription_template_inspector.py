import json

from services.team_prescription_template_inspector import find_team_template_inspection


def test_inspector_resolves_published_template_and_exposes_known_unknown_fields(tmp_path) -> None:
    payload = {
        "schema_version": 1,
        "catalog_version": "u50-test",
        "game_update": "Update 50",
        "templates": [
            {
                "template_id": "u50-gs-dd-dk",
                "name": "U50 Godslayer Dragonknight DD",
                "source_name": "BTV Tools",
                "source_url": "https://example.invalid/source",
                "retrieved_at": "2026-09-04",
                "base_score": 10,
                "slot_scores": {"DD 1": 100},
                "goal_scores": {"Godslayer": 25},
                "complete_build": False,
                "unresolved": ["gear, skills, CP, food, and potion remain unresolved"],
                "build": {
                    "BuildName": "U50 Godslayer Dragonknight DD",
                    "EsoClass": "Dragonknight",
                    "Role": "DD",
                },
            }
        ],
    }
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    inspection = find_team_template_inspection(
        data_dir=tmp_path,
        slot_name="DD 1",
        build_name="U50 Godslayer Dragonknight DD",
        eso_class="Dragonknight",
    )

    assert inspection is not None
    assert inspection.template_id == "u50-gs-dd-dk"
    assert inspection.template_kind == "Published reference template"
    assert inspection.eso_class == "Dragonknight"
    assert inspection.role == "DD"
    assert not inspection.complete_build
    assert inspection.known_fields == ("class", "role")
    assert "gear, skills, CP" in inspection.unknown_fields[0]


def test_inspector_does_not_match_wrong_role_or_class(tmp_path) -> None:
    payload = {
        "schema_version": 1,
        "catalog_version": "u50-test",
        "game_update": "Update 50",
        "templates": [
            {
                "template_id": "warden-healer",
                "name": "Warden Healer",
                "source_name": "Reference",
                "source_url": "https://example.invalid/source",
                "retrieved_at": "2026-09-04",
                "base_score": 1,
                "slot_scores": {},
                "goal_scores": {},
                "complete_build": False,
                "unresolved": [],
                "build": {
                    "BuildName": "Warden Healer",
                    "EsoClass": "Warden",
                    "Role": "Healer",
                },
            }
        ],
    }
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    assert find_team_template_inspection(
        data_dir=tmp_path,
        slot_name="DD 1",
        build_name="Warden Healer",
        eso_class="Warden",
    ) is None
    assert find_team_template_inspection(
        data_dir=tmp_path,
        slot_name="Healer 1",
        build_name="Warden Healer",
        eso_class="Arcanist",
    ) is None
