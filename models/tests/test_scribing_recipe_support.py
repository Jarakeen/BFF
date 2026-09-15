from pathlib import Path

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
from ui import scribing_support
from ui.scribing_support import _recipes_for, _store_recipes


def test_uesp_scribing_catalog_has_expected_shape():
    assert len(grimoire_names()) == 12
    assert "Damage Shield" in compatible_focus("Soul Burst")
    assert "Lingering Torment" in compatible_signature("Soul Burst")
    assert "Courage" in compatible_affix("Soul Burst")
    assert skill_line_for_grimoire("Soul Burst") == "Soul Magic"
    assert result_name("Soul Burst", "Damage Shield") == "Warding Burst"


def test_verified_magical_banner_result_name_is_explicit():
    assert "Magic Damage" in compatible_focus("Banner Bearer")
    assert skill_line_for_grimoire("Banner Bearer") == "Support"
    assert result_name("Banner Bearer", "Magic Damage") == "Magical Banner"


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


def test_player_build_natively_round_trips_scribing_recipe_without_ui_install():
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


def test_player_build_natively_migrates_legacy_scribed_names_without_ui_install():
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


def test_scribing_ui_does_not_replace_player_build_serialization_methods():
    source = Path(scribing_support.__file__).read_text(encoding="utf-8")

    assert "PlayerBuild.to_dict =" not in source
    assert "PlayerBuild.from_dict =" not in source
    assert "original_to_dict" not in source
    assert "original_from_dict" not in source
