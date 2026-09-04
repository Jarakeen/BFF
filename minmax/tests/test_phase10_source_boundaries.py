from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from models.build_model import GearSlot, PlayerBuild
from models.scribing_recipe import ScribedSkillRecipe
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService


class _MissingGearRepository:
    def get_set(self, _name):
        return None


class _UnusedGearResolver:
    def resolve(self, *_args, **_kwargs):
        raise AssertionError("legacy gear resolver must not be called for entity-only source boundary")


def _service(database_path):
    service = SavedBuildCapabilityService(
        BuildService(database_path.parent / "builds.json"),
        database_path,
        context_factory=SimpleNamespace(),
        progression=SimpleNamespace(),
        skills=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        gear=_UnusedGearResolver(),
        potions=SimpleNamespace(),
    )
    service.gear_repository = _MissingGearRepository()
    return service


def test_complete_canonically_compatible_scribed_recipe_is_boundary_not_gap(tmp_path):
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE ability(ability_id INTEGER PRIMARY KEY, name TEXT, class_type TEXT, rank INTEGER, morph INTEGER, is_crafted INTEGER)"
        )
        db.execute(
            "INSERT INTO ability VALUES (1, 'Leashing Soul', '', 1, 0, 1)"
        )

    build = PlayerBuild(
        Name="Susan",
        BuildName="Necro Tank",
        FrontBarSkills=["Leashing Soul", "", "", "", "", ""],
        ScribedSkills=["Leashing Soul"],
        ScribedSkillRecipes=[
            ScribedSkillRecipe(
                ResultName="Leashing Soul",
                Grimoire="Wield Soul",
                Focus="Pull",
                Signature="Druid's Resurgence",
                Affix="Cowardice",
            )
        ],
    )
    service = _service(database)
    gaps: list[str] = []
    boundaries: list[str] = []

    effects = service._skill_variants(build, "front", gaps, boundaries)

    assert effects == []
    assert gaps == []
    assert boundaries == [
        "front configured scribed skill recipe resolved; detailed scripted effect conversion deferred: "
        "Leashing Soul [Wield Soul | Pull | Druid's Resurgence | Cowardice]"
    ]


def test_incomplete_scribed_recipe_remains_capability_gap(tmp_path):
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE ability(ability_id INTEGER PRIMARY KEY, name TEXT, class_type TEXT, rank INTEGER, morph INTEGER, is_crafted INTEGER)"
        )
        db.execute("INSERT INTO ability VALUES (1, 'Leashing Soul', '', 1, 0, 1)")

    build = PlayerBuild(
        FrontBarSkills=["Leashing Soul", "", "", "", "", ""],
        ScribedSkills=["Leashing Soul"],
        ScribedSkillRecipes=[ScribedSkillRecipe(ResultName="Leashing Soul")],
    )
    service = _service(database)
    gaps: list[str] = []
    boundaries: list[str] = []

    service._skill_variants(build, "front", gaps, boundaries)

    assert gaps == [
        "front scribed skill requires configured recipe semantics before capability resolution: Leashing Soul"
    ]
    assert boundaries == []


def test_entity_backed_gear_identity_is_boundary_when_legacy_effect_table_lacks_set(tmp_path):
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE entity(id TEXT PRIMARY KEY, entity_type TEXT, name TEXT, slug TEXT)"
        )
        db.execute(
            "CREATE TABLE entity_source(entity_id TEXT, source TEXT, source_entity_type TEXT)"
        )
        db.execute(
            "INSERT INTO entity VALUES ('gear_set:perfected_puncturing_remedy', 'gear_set', 'Perfected Puncturing Remedy', 'perfected_puncturing_remedy')"
        )
        db.execute(
            "INSERT INTO entity_source VALUES ('gear_set:perfected_puncturing_remedy', 'ESO-Hub', 'gear_set')"
        )

    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Perfected Puncturing Remedy", WeaponType="Sword")
    )
    service = _service(database)
    gaps: list[str] = []
    boundaries: list[str] = []

    effects = service._gear_variants(build, "front", gaps, boundaries)

    assert effects == []
    assert gaps == []
    assert boundaries == [
        "front gear set identity resolved from canonical entity/source data; "
        "legacy gear_set effect semantics unavailable: Perfected Puncturing Remedy"
    ]


def test_unknown_gear_still_remains_capability_gap(tmp_path):
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE entity(id TEXT PRIMARY KEY, entity_type TEXT, name TEXT, slug TEXT)"
        )

    build = PlayerBuild(FrontBarWeapon=GearSlot(Set="Definitely Not A Real Set", WeaponType="Sword"))
    service = _service(database)
    gaps: list[str] = []
    boundaries: list[str] = []

    service._gear_variants(build, "front", gaps, boundaries)

    assert gaps == ["front gear set not found in canonical data: Definitely Not A Real Set"]
    assert boundaries == []