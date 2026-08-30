from models.build_model import PlayerBuild
from models.scribing_recipe import ScribedSkillRecipe
from services.scribing_catalog import (
    compatible_affix,
    compatible_focus,
    compatible_signature,
    grimoire_names,
    result_name,
    skill_line_for_grimoire,
)
from ui.scribing_support import _recipes_for, _store_recipes, install


def test_uesp_scribing_catalog_has_expected_shape():
    assert len(grimoire_names()) == 12
    assert "Damage Shield" in compatible_focus("Soul Burst")
    assert "Lingering Torment" in compatible_signature("Soul Burst")
    assert "Courage" in compatible_affix("Soul Burst")
    assert skill_line_for_grimoire("Soul Burst") == "Soul Magic"
    assert result_name("Soul Burst", "Damage Shield") == "Warding Burst"


def test_recipe_store_keeps_legacy_name_mirror():
    build = PlayerBuild(Name="Tank")
    recipe = ScribedSkillRecipe(
        ResultName="Warding Burst",
        Grimoire="Soul Burst",
        Focus="Damage Shield",
        Signature="Lingering Torment",
        Affix="Courage",
    )

    _store_recipes(build, [recipe])

    assert build.ScribedSkills == ["Warding Burst"]
    assert _recipes_for(build) == [recipe]


def test_installed_player_build_serialization_round_trips_recipe():
    install()
    build = PlayerBuild(Name="Tank")
    recipe = ScribedSkillRecipe(
        ResultName="Warding Burst",
        Grimoire="Soul Burst",
        Focus="Damage Shield",
        Signature="Lingering Torment",
        Affix="Courage",
    )
    _store_recipes(build, [recipe])

    payload = build.to_dict()
    restored = PlayerBuild.from_dict(payload)

    assert payload["ScribedSkills"] == ["Warding Burst"]
    assert payload["ScribedSkillRecipes"] == [recipe.to_dict()]
    assert restored.ScribedSkills == ["Warding Burst"]
    assert _recipes_for(restored) == [recipe]


def test_installed_player_build_migrates_legacy_scribed_names():
    install()
    restored = PlayerBuild.from_dict(
        {
            "Name": "Legacy Tank",
            "ScribedSkills": ["Warding Burst"],
        }
    )

    recipes = _recipes_for(restored)
    assert len(recipes) == 1
    assert recipes[0].ResultName == "Warding Burst"
    assert recipes[0].Grimoire == ""
