from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.character_progression_service import CharacterProgressionService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.rotation_progression_readiness_service import RotationProgressionReadinessService


def _catalog(tmp_path) -> BuildCatalogService:
    service = BuildCatalogService(tmp_path / "characters.json")
    service.save(
        {
            "schema_version": 3,
            "characters": [
                {
                    "character_id": "char-magrat",
                    "name": "Magrat",
                    "gamertag": "Jarakeen",
                    "eso_class": "Warden",
                    "race": "Breton",
                    "role": "Healer",
                    "owned_skill_lines": [],
                    "passive_ranks": {},
                    "passive_cp_points": {},
                }
            ],
            "builds": [],
        }
    )
    return service


def _build() -> PlayerBuild:
    build = PlayerBuild()
    build.Name = "Magrat"
    build.Gamertag = "Jarakeen"
    build.BuildName = "DF Healer"
    build.AttributeMagicka = 64
    build.Armor["Chest"]["Weight"] = "Light"
    build.Armor["Head"]["Weight"] = "Medium"
    return build


def test_saving_light_armor_progression_flips_magicka_readiness_to_ready(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    build = _build()
    readiness = RotationProgressionReadinessService(
        MinmaxCharacterProgressionAdapter(catalog)
    )

    before = readiness.assess(build=build, resource=ResourceType.MAGICKA)
    assert before.ready is False
    assert before.missing_cost_relevant_skill_lines == ("Light Armor",)

    saved = CharacterProgressionService(catalog).save(
        character_id="char-magrat",
        owned_skill_lines=["Light Armor"],
        passive_ranks={},
        passive_cp_points={},
    )

    assert saved is not None
    assert saved.owned_skill_lines == ("Light Armor",)

    after = readiness.assess(build=build, resource=ResourceType.MAGICKA)
    assert after.ready is True
    assert after.canonical_owned_skill_lines == ("Light Armor",)
    assert after.missing_cost_relevant_skill_lines == ()
    assert after.unresolved == ()


def test_character_progression_save_is_shared_across_builds_for_same_character(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    progression = CharacterProgressionService(catalog)
    progression.save(
        character_id="char-magrat",
        owned_skill_lines=["Light Armor", "Medium Armor"],
        passive_ranks={},
        passive_cp_points={},
    )

    df_healer = _build()
    gh_healer = _build()
    gh_healer.BuildName = "GH Healer"

    readiness = RotationProgressionReadinessService(
        MinmaxCharacterProgressionAdapter(catalog)
    )

    df_magicka = readiness.assess(build=df_healer, resource=ResourceType.MAGICKA)
    gh_stamina = readiness.assess(build=gh_healer, resource=ResourceType.STAMINA)

    assert df_magicka.ready is True
    assert gh_stamina.ready is True
    assert df_magicka.canonical_owned_skill_lines == ("Light Armor", "Medium Armor")
    assert gh_stamina.canonical_owned_skill_lines == ("Light Armor", "Medium Armor")
