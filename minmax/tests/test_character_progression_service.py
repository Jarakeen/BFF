from __future__ import annotations

from services.build_catalog_service import BuildCatalogService
from services.character_progression_service import CharacterProgressionService


def _catalog(tmp_path):
    service = BuildCatalogService(tmp_path / "characters.json")
    service.save(
        {
            "schema_version": 3,
            "characters": [
                {
                    "character_id": "char-1",
                    "name": "Magrat",
                    "gamertag": "Jarakeen",
                    "eso_class": "Warden",
                    "owned_skill_lines": [],
                    "passive_ranks": {},
                    "passive_cp_points": {},
                }
            ],
            "builds": [
                {
                    "build_id": "build-a",
                    "character_id": "char-1",
                    "name": "Healer",
                    "payload": {"Potion": "spell power"},
                    "legacy": {"Potion": "spell power"},
                },
                {
                    "build_id": "build-b",
                    "character_id": "char-1",
                    "name": "Support DD",
                    "payload": {},
                    "legacy": {},
                },
            ],
        }
    )
    return service


def test_progression_persists_on_character_not_builds(tmp_path):
    catalog = _catalog(tmp_path)
    service = CharacterProgressionService(catalog)

    saved = service.save(
        character_id="char-1",
        owned_skill_lines=["Light Armor", "Undaunted"],
        passive_ranks={"Medicinal Use": 3, "Flourish": 2},
        passive_cp_points={"Boundless Vitality": 50, "Fortification": 30},
    )

    assert saved is not None
    assert saved.owned_skill_lines == ("Light Armor", "Undaunted")
    assert saved.passive_ranks == {"Medicinal Use": 3, "Flourish": 2}
    assert saved.passive_cp_points == {"Boundless Vitality": 50, "Fortification": 30}

    data = catalog.load()
    assert data["characters"][0]["passive_cp_points"] == {
        "Boundless Vitality": 50,
        "Fortification": 30,
    }
    assert "passive_ranks" not in data["builds"][0]
    assert "passive_cp_points" not in data["builds"][0]
    assert "passive_ranks" not in data["builds"][1]
    assert "passive_cp_points" not in data["builds"][1]


def test_progression_preserves_explicit_zero_values(tmp_path):
    catalog = _catalog(tmp_path)
    service = CharacterProgressionService(catalog)

    service.save(
        character_id="char-1",
        owned_skill_lines=["Light Armor", "light armor", ""],
        passive_ranks={"Medicinal Use": 0, "Flourish": 2},
        passive_cp_points={"Fortification": 0, "Boundless Vitality": 50},
    )

    saved = service.get("char-1")
    assert saved is not None
    assert saved.owned_skill_lines == ("Light Armor",)
    assert saved.passive_ranks == {"Medicinal Use": 0, "Flourish": 2}
    assert saved.passive_cp_points == {"Fortification": 0, "Boundless Vitality": 50}


def test_progression_finds_character_by_account_and_name(tmp_path):
    catalog = _catalog(tmp_path)
    service = CharacterProgressionService(catalog)

    assert service.find_character_id(name=" magrat ", gamertag="JARAKEEN") == "char-1"
    assert service.find_character_id(name="Other", gamertag="Jarakeen") is None
