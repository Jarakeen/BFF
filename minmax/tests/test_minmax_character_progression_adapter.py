from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.character_progression_service import CharacterProgressionService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


def _catalog(tmp_path):
    catalog = BuildCatalogService(tmp_path / "characters.json")
    catalog.save(
        {
            "schema_version": 3,
            "characters": [
                {
                    "character_id": "char-1",
                    "name": "Alice",
                    "gamertag": "AliceGT",
                    "eso_class": "Warden",
                    "race": "Breton",
                }
            ],
            "builds": [],
        }
    )
    return catalog


def test_adapter_carries_character_progression_and_explicit_zero(tmp_path):
    catalog = _catalog(tmp_path)
    CharacterProgressionService(catalog).save(
        character_id="char-1",
        owned_skill_lines=["Undaunted", "Light Armor"],
        passive_ranks={"Medicinal Use": 0, "Undaunted Mettle": 2},
        passive_cp_points={"Fortification": 0, "Boundless Vitality": 50},
    )
    build = PlayerBuild(
        Name="Alice",
        Gamertag="AliceGT",
        BuildName="Healer",
        AttributeMagicka=64,
    )

    result = MinmaxCharacterProgressionAdapter(catalog).resolve(build)

    assert result.resolved
    assert result.character_id == "char-1"
    assert result.progression.attributes.magicka == 64
    assert result.progression.owns_skill_line("undaunted")
    assert result.progression.passive_rank("Medicinal Use") == 0
    assert result.progression.passive_rank("Undaunted Mettle") == 2
    assert result.progression.passive_cp_allocation("Fortification") == 0
    assert result.progression.passive_cp_allocation("Boundless Vitality") == 50


def test_adapter_missing_character_keeps_progression_unknown(tmp_path):
    catalog = BuildCatalogService(tmp_path / "characters.json")
    build = PlayerBuild(
        Name="Missing",
        Gamertag="Nobody",
        AttributeHealth=64,
    )

    result = MinmaxCharacterProgressionAdapter(catalog).resolve(build)

    assert not result.resolved
    assert result.character_id == ""
    assert result.progression.attributes.health == 64
    assert result.progression.passive_ranks is None
    assert result.progression.passive_cp_points is None
    assert result.unresolved == (
        "Canonical character progression could not be resolved for saved build",
    )
