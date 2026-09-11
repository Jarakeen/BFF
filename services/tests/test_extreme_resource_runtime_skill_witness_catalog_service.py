from services.extreme_resource_runtime_skill_witness_catalog_service import (
    ExtremeResourceRuntimeSkillWitness,
    ExtremeResourceRuntimeSkillWitnessCatalogService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


class _Skills:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def actives(self):
        return self.rows


def _row(
    *,
    skill_id,
    name,
    line,
    skill_type="Active",
    description="",
    domain=ExtremeSkillDomain.CLASS,
    ability_id=...,
):
    return ExtremePlayerSkillRecord(
        skill_id=skill_id,
        name=name,
        class_type="",
        skill_line=line,
        skill_type=skill_type,
        is_passive=False,
        is_player=True,
        is_crafted=False,
        base_ability_id=skill_id * 10,
        max_rank=4,
        max_rank_ability_id=(skill_id * 100 if ability_id is ... else ability_id),
        description=description,
        domain=domain,
    )


def test_catalog_resolves_armor_pet_and_transformation_witness_families():
    service = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(
            (
                _row(
                    skill_id=1,
                    name="Harness Magicka",
                    line="Light Armor",
                    description="Create a shield around yourself.",
                    domain=ExtremeSkillDomain.ARMOR,
                ),
                _row(
                    skill_id=2,
                    name="Summon Twilight Matriarch",
                    line="Daedric Summoning",
                    description="Call on Azura to summon a twilight matriarch to fight at your side.",
                ),
                _row(
                    skill_id=3,
                    name="Werewolf Transformation",
                    line="Werewolf",
                    skill_type="Ultimate",
                    description="Transform into a beast, increasing your combat prowess.",
                    domain=ExtremeSkillDomain.WORLD,
                ),
            )
        )
    )

    catalog = service.build()

    assert catalog.denominator_proven is True
    assert catalog.active_skills_reviewed == 3
    assert [row.canonical_id for row in catalog.armor_abilities] == ["harness_magicka"]
    assert [row.canonical_id for row in catalog.pet_abilities] == ["summon_twilight_matriarch"]
    assert [row.canonical_id for row in catalog.transformation_ultimates] == ["werewolf_transformation"]
    assert catalog.unresolved == ()


def test_pet_witness_accepts_persistent_companion_grammar_without_literal_summon_prefix():
    service = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(
            (
                _row(skill_id=1, name="Annulment", line="Light Armor", domain=ExtremeSkillDomain.ARMOR),
                _row(
                    skill_id=2,
                    name="Summon Unstable Familiar",
                    line="Daedric Summoning",
                    description=(
                        "Command the powers of Oblivion to send a Daedric familiar to fight at your side. "
                        "The familiar remains until killed or unsummoned."
                    ),
                ),
                _row(
                    skill_id=3,
                    name="Feral Guardian",
                    line="Animal Companions",
                    skill_type="Ultimate",
                    description=(
                        "Rouse a grizzly to fight by your side. Once summoned you can activate "
                        "Guardian's Wrath."
                    ),
                ),
                _row(
                    skill_id=4,
                    name="Werewolf Transformation",
                    line="Werewolf",
                    skill_type="Ultimate",
                    description="Transform into a beast.",
                    domain=ExtremeSkillDomain.WORLD,
                ),
            )
        )
    )

    catalog = service.build()

    assert [row.canonical_id for row in catalog.pet_abilities] == [
        "feral_guardian",
        "summon_unstable_familiar",
    ]
    assert catalog.denominator_proven is True


def test_pet_witness_requires_a_summoned_creature_not_environmental_construct():
    service = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(
            (
                _row(skill_id=1, name="Harness Magicka", line="Light Armor", domain=ExtremeSkillDomain.ARMOR),
                _row(
                    skill_id=2,
                    name="Grave Grasp",
                    line="Bone Tyrant",
                    description="Summon three patches of skeletal claws from the ground.",
                ),
                _row(
                    skill_id=3,
                    name="Bone Goliath Transformation",
                    line="Bone Tyrant",
                    skill_type="Ultimate",
                    description="Transform into a horrific Bone Goliath.",
                ),
            )
        )
    )

    catalog = service.build()

    assert catalog.pet_abilities == ()
    assert catalog.denominator_proven is False
    assert any("pet_active" in item for item in catalog.unresolved)


def test_sparse_canonical_transformation_row_keeps_semantic_identity():
    service = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(
            (
                _row(skill_id=1, name="Annulment", line="Light Armor", domain=ExtremeSkillDomain.ARMOR),
                _row(
                    skill_id=2,
                    name="Summon Familiar",
                    line="Daedric Summoning",
                    description="Summon a familiar to fight for you.",
                ),
                _row(
                    skill_id=3,
                    name="Werewolf Transformation",
                    line="Werewolf",
                    skill_type="",
                    description="Transform into a beast.",
                    domain=ExtremeSkillDomain.WORLD,
                    ability_id=None,
                ),
            )
        )
    )

    catalog = service.build()

    assert catalog.denominator_proven is True
    witness = catalog.transformation_ultimates[0]
    assert witness.canonical_id == "werewolf_transformation"
    assert witness.canonical_skill_line_id == "werewolf"


def test_numeric_alias_changes_do_not_change_canonical_witness_identity():
    left = ExtremeResourceRuntimeSkillWitness(
        condition="pet_active",
        skill_id=100,
        base_ability_id=200,
        ability_id=300,
        name="Summon Unstable Familiar",
        skill_line="Daedric Summoning",
        skill_type="Active",
        description="reviewed",
    )
    right = ExtremeResourceRuntimeSkillWitness(
        condition="pet_active",
        skill_id=101,
        base_ability_id=201,
        ability_id=999999,
        name="Summon Unstable Familiar",
        skill_line="Daedric Summoning",
        skill_type="Active",
        description="same semantic skill, different observed ids",
    )

    assert left.identity == right.identity
    assert left.identity == ("pet_active", "summon_unstable_familiar", "daedric_summoning")


def test_transformation_witness_rejects_unreviewed_nonultimate_world_skill():
    service = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(
            (
                _row(skill_id=1, name="Harness Magicka", line="Light Armor", domain=ExtremeSkillDomain.ARMOR),
                _row(
                    skill_id=2,
                    name="Summon Familiar",
                    line="Daedric Summoning",
                    description="Summon a familiar to fight for you.",
                ),
                _row(
                    skill_id=3,
                    name="Fake Transformation",
                    line="World",
                    description="Transform into something temporarily.",
                    domain=ExtremeSkillDomain.WORLD,
                ),
            )
        )
    )

    catalog = service.build()

    assert catalog.transformation_ultimates == ()
    assert catalog.denominator_proven is False


def test_empty_skill_universe_fails_closed():
    catalog = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(())
    ).build()

    assert catalog.denominator_proven is False
    assert catalog.active_skills_reviewed == 0
    assert len(catalog.unresolved) == 4
