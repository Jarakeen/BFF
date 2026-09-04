import json
from pathlib import Path

import pytest

from services.team_composition_catalog import (
    TeamCompositionCatalog,
    find_composition_template,
    flexible_raid_slots,
)


def _payload() -> dict:
    return {
        "schema_version": 1,
        "catalog_version": "u50-test.1",
        "game_update": "Update 50",
        "templates": [
            {
                "template_id": "godslayer-test",
                "name": "Godslayer Test Comp",
                "trial_name": "Sunspire",
                "goal": "Godslayer",
                "difficulty": "Veteran Hardmode",
                "game_update": "Update 50",
                "sources": [
                    {
                        "name": "Example Source",
                        "url": "https://example.com/comp",
                        "retrieved_at": "2026-09-04",
                        "note": "Composition evidence only.",
                    }
                ],
                "slots": [
                    {
                        "slot_name": "Main Tank",
                        "role": "Tank",
                        "preferred_class": "Dragonknight",
                        "alternative_classes": ["Necromancer"],
                        "required_responsibilities": ["Boss positioning"],
                        "optional_responsibilities": ["Defensive flex"],
                        "provider_requirements": ["Major Breach coverage"],
                        "mechanic_jobs": ["Primary boss positioning"],
                    },
                    {
                        "slot_name": "Healer 1",
                        "role": "Healer",
                        "preferred_class": "Warden",
                    },
                ],
            }
        ],
    }


def _write(tmp_path, payload: dict) -> Path:
    path = tmp_path / "team_compositions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_catalog_loads_versioned_composition_evidence(tmp_path) -> None:
    snapshot = TeamCompositionCatalog(_write(tmp_path, _payload())).load()

    assert snapshot.catalog_version == "u50-test.1"
    assert snapshot.game_update == "Update 50"
    assert len(snapshot.templates) == 1
    template = snapshot.templates[0]
    assert template.goal == "Godslayer"
    assert template.trial_name == "Sunspire"
    assert template.slots[0].preferred_class == "Dragonknight"
    assert template.slots[0].alternative_classes == ("Necromancer",)
    assert template.slots[0].required_responsibilities == ("Boss positioning",)
    assert template.slots[0].optional_responsibilities == ("Defensive flex",)
    assert template.slots[0].provider_requirements == ("Major Breach coverage",)
    assert template.slots[0].mechanic_jobs == ("Primary boss positioning",)
    assert template.sources[0].name == "Example Source"


def test_legacy_responsibilities_field_remains_compatible(tmp_path) -> None:
    payload = _payload()
    slot = payload["templates"][0]["slots"][0]
    slot.pop("required_responsibilities")
    slot["responsibilities"] = ["Legacy required duty"]

    snapshot = TeamCompositionCatalog(_write(tmp_path, payload)).load()

    assert snapshot.templates[0].slots[0].required_responsibilities == (
        "Legacy required duty",
    )


def test_goal_lookup_does_not_leak_godslayer_into_swashbuckler(tmp_path) -> None:
    snapshot = TeamCompositionCatalog(_write(tmp_path, _payload())).load()

    assert find_composition_template(
        snapshot,
        goal="Godslayer",
        difficulty="Veteran Hardmode",
    ) is not None
    assert find_composition_template(
        snapshot,
        goal="Swashbuckler Supreme",
        difficulty="Veteran Hardmode",
    ) is None


def test_flexible_raid_skeleton_is_two_two_eight_without_fake_classes() -> None:
    slots = flexible_raid_slots(12)

    assert len(slots) == 12
    assert [slot.role for slot in slots[:4]] == ["Tank", "Tank", "Healer", "Healer"]
    assert sum(slot.role == "DD" for slot in slots) == 8
    assert all(slot.preferred_class == "Any class" for slot in slots)
    assert all(not slot.required_responsibilities for slot in slots)
    assert all(not slot.provider_requirements for slot in slots)
    assert all(not slot.mechanic_jobs for slot in slots)


def test_real_u50_catalog_contains_complete_godslayer_raid_matrix() -> None:
    root = Path(__file__).resolve().parents[2]
    snapshot = TeamCompositionCatalog(root / "data" / "team_compositions.json").load()
    template = find_composition_template(
        snapshot,
        goal="Godslayer",
        difficulty="Veteran Hardmode",
    )

    assert template is not None
    assert template.trial_name == "Sunspire"
    assert len(template.slots) == 12
    assert [slot.preferred_class for slot in template.slots[:4]] == [
        "Dragonknight",
        "Sorcerer",
        "Warden",
        "Arcanist",
    ]
    group_healer = template.slots[2]
    assert group_healer.slot_name == "Healer 1"
    assert group_healer.preferred_class == "Warden"
    assert "Group Healer" in group_healer.required_responsibilities
    assert "Major Courage coverage" in group_healer.provider_requirements
    assert group_healer.mechanic_jobs
    assert len(template.sources) >= 2


def test_catalog_rejects_duplicate_template_ids(tmp_path) -> None:
    payload = _payload()
    payload["templates"].append(dict(payload["templates"][0]))

    with pytest.raises(ValueError, match="duplicate team composition template_id"):
        TeamCompositionCatalog(_write(tmp_path, payload)).load()
