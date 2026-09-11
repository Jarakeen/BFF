from services.extreme_resource_runtime_skill_witness_catalog_service import (
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
    ability_id=None,
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
        max_rank_ability_id=ability_id if ability_id is not None else skill_id * 100,
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
    assert [row.name for row in catalog.armor_abilities] == ["Harness Magicka"]
    assert [row.name for row in catalog.pet_abilities] == ["Summon Twilight Matriarch"]
    assert [row.name for row in catalog.transformation_ultimates] == ["Werewolf Transformation"]
    assert catalog.unresolved == ()


def test_pet_witness_requires_explicit_summon_evidence_not_merely_a_class_line():
    service = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(
            (
                _row(
                    skill_id=1,
                    name="Harness Magicka",
                    line="Light Armor",
                    domain=ExtremeSkillDomain.ARMOR,
                ),
                _row(
                    skill_id=2,
                    name="Daedric Curse",
                    line="Daedric Summoning",
                    description="Curse an enemy with a destructive rune.",
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


def test_transformation_witness_must_be_an_ultimate():
    service = ExtremeResourceRuntimeSkillWitnessCatalogService(
        skill_universe_service=_Skills(
            (
                _row(
                    skill_id=1,
                    name="Harness Magicka",
                    line="Light Armor",
                    domain=ExtremeSkillDomain.ARMOR,
                ),
                _row(
                    skill_id=2,
                    name="Summon Familiar",
                    line="Daedric Summoning",
                    description="Summon a familiar pet to fight for you.",
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
