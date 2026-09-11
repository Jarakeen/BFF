from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_resource_runtime_skill_witness_catalog_service import (
    ExtremeResourceRuntimeSkillWitness,
    ExtremeResourceRuntimeSkillWitnessCatalog,
)
from services.extreme_resource_runtime_skill_witness_materialization_service import (
    ExtremeResourceRuntimeSkillWitnessMaterializationService,
)


class _CatalogService:
    def __init__(self, catalog):
        self.catalog = catalog

    def build(self):
        return self.catalog


def _witness(condition, name, line, *, ultimate=False, skill_id=1):
    return ExtremeResourceRuntimeSkillWitness(
        condition=condition,
        skill_id=skill_id,
        base_ability_id=skill_id * 10,
        ability_id=skill_id * 100,
        name=name,
        skill_line=line,
        skill_type="Ultimate" if ultimate else "Active",
        description="reviewed witness",
    )


def _catalog(*, armor=(), pets=(), transforms=(), denominator_proven=True, unresolved=()):
    return ExtremeResourceRuntimeSkillWitnessCatalog(
        armor_abilities=tuple(armor),
        pet_abilities=tuple(pets),
        transformation_ultimates=tuple(transforms),
        active_skills_reviewed=216,
        denominator_proven=denominator_proven,
        unresolved=tuple(unresolved),
    )


def _route(*lines):
    return SimpleNamespace(equipped_skill_lines=tuple(lines))


def test_materializes_armor_pet_and_werewolf_with_real_slot_competition():
    service = ExtremeResourceRuntimeSkillWitnessMaterializationService(
        catalog_service=_CatalogService(
            _catalog(
                armor=(
                    _witness(
                        "armor_ability_slotted",
                        "Annulment",
                        "Light Armor",
                        skill_id=1,
                    ),
                ),
                pets=(
                    _witness(
                        "pet_active",
                        "Summon Unstable Familiar",
                        "Daedric Summoning",
                        skill_id=2,
                    ),
                ),
                transforms=(
                    _witness(
                        "transformed",
                        "Werewolf Transformation",
                        "Werewolf",
                        ultimate=True,
                        skill_id=3,
                    ),
                ),
            )
        )
    )
    build = PlayerBuild(
        FrontBarSkills=["A", "B", "C", "D", "E", "Old Ultimate"],
        Armor={"Head": {"Weight": "Light"}},
    )

    result = service.materialize(
        build=build,
        route=_route("Daedric Summoning", "Dark Magic", "Storm Calling"),
        required_conditions=(
            "armor_ability_slotted",
            "pet_active",
            "transformed",
        ),
        active_bar="front",
    )

    assert result.projection_complete is True
    assert result.active_conditions == (
        "armor_ability_slotted",
        "pet_active",
        "transformed",
    )
    assert result.build.FrontBarSkills[:3] == ["A", "B", "C"]
    assert result.build.FrontBarSkills[3:5] == [
        "Summon Unstable Familiar",
        "Annulment",
    ]
    assert result.build.FrontBarSkills[5] == "Werewolf Transformation"
    assert result.build.Werewolf is True
    assert result.build.Vampire is False
    assert (4, "E") in result.displaced_skills
    assert (3, "D") in result.displaced_skills
    assert (5, "Old Ultimate") in result.displaced_skills


def test_pet_condition_fails_closed_when_route_cannot_slot_any_catalog_pet():
    service = ExtremeResourceRuntimeSkillWitnessMaterializationService(
        catalog_service=_CatalogService(
            _catalog(
                armor=(_witness("armor_ability_slotted", "Annulment", "Light Armor"),),
                pets=(
                    _witness(
                        "pet_active",
                        "Summon Unstable Familiar",
                        "Daedric Summoning",
                        skill_id=2,
                    ),
                ),
                transforms=(
                    _witness(
                        "transformed",
                        "Werewolf Transformation",
                        "Werewolf",
                        ultimate=True,
                        skill_id=3,
                    ),
                ),
            )
        )
    )

    result = service.materialize(
        build=PlayerBuild(),
        route=_route("Green Balance", "Animal Companions", "Winter's Embrace"),
        required_conditions=("pet_active",),
    )

    assert result.projection_complete is False
    assert result.active_conditions == ()
    assert any("selected Extreme class route" in item for item in result.unresolved)


def test_armor_condition_requires_a_worn_matching_armor_weight():
    service = ExtremeResourceRuntimeSkillWitnessMaterializationService(
        catalog_service=_CatalogService(
            _catalog(
                armor=(_witness("armor_ability_slotted", "Annulment", "Light Armor"),),
                pets=(_witness("pet_active", "Summon Shade", "Shadow", skill_id=2),),
                transforms=(
                    _witness(
                        "transformed",
                        "Werewolf Transformation",
                        "Werewolf",
                        ultimate=True,
                        skill_id=3,
                    ),
                ),
            )
        )
    )

    result = service.materialize(
        build=PlayerBuild(Armor={"Chest": {"Weight": "Heavy"}}),
        route=_route("Shadow", "Siphoning", "Assassination"),
        required_conditions=("armor_ability_slotted",),
    )

    assert result.projection_complete is False
    assert result.active_conditions == ()
    assert any("worn armor weights" in item for item in result.unresolved)


def test_catalog_failure_remains_visible_and_prevents_projection_closure():
    service = ExtremeResourceRuntimeSkillWitnessMaterializationService(
        catalog_service=_CatalogService(
            _catalog(
                denominator_proven=False,
                unresolved=("No canonical transformation Ultimate witness is available for transformed",),
            )
        )
    )

    result = service.materialize(
        build=PlayerBuild(),
        route=_route("Green Balance"),
        required_conditions=("transformed",),
    )

    assert result.projection_complete is False
    assert result.active_conditions == ()
    assert "No canonical transformation Ultimate witness is available for transformed" in result.unresolved
