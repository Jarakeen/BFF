from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, description: str, *, line: str = "Test Line", domain=ExtremeSkillDomain.CLASS):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="Test Class" if domain is ExtremeSkillDomain.CLASS else "",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description=description,
        domain=domain,
    )


class _Universe:
    def passives(self):
        return (
            _passive("Last Gasp", "Increases your Max Health by 1250."),
            _passive("Deep Reserves", "Increases your Max Magicka by 8%."),
            _passive(
                "Triune Mind",
                "Increases your Max Health, Magicka, and Stamina by 4%.",
            ),
            _passive(
                "Tough",
                "Increases your Max Health by 2000.",
                line="Imperial Skills",
                domain=ExtremeSkillDomain.RACIAL,
            ),
            _passive(
                "Juggernaut",
                "Increases your Max Health by 2% for each piece of Heavy Armor equipped.",
                line="Heavy Armor",
                domain=ExtremeSkillDomain.ARMOR,
            ),
            _passive(
                "Magicka Controller",
                "Increases your Max Magicka and Magicka Recovery for each Mages Guild ability slotted.",
                line="Mages Guild",
                domain=ExtremeSkillDomain.GUILD,
            ),
            _passive("Mystery", "Something mechanically mysterious happens."),
        )


class _RaceRepository:
    def get_stat_map_by_name(self, name):
        if name == "Imperial":
            return {"max_health": 2000.0, "max_stamina": 2000.0}
        return {}


def test_projection_recognizes_static_max_resource_flat_and_percent_clauses():
    health = ExtremePassiveProjectionService.project(
        _passive("Last Gasp", "Increases your Max Health by 1250.")
    )
    assert health.status is ExtremePassiveProjectionStatus.REVIEWED_STATIC
    assert [(row.objective_key, row.flat) for row in health.contributions] == [
        ("max_health", 1250.0)
    ]

    magicka = ExtremePassiveProjectionService.project(
        _passive("Deep Reserves", "Increases your Max Magicka by 8%.")
    )
    assert magicka.status is ExtremePassiveProjectionStatus.REVIEWED_STATIC
    assert magicka.contributions[0].objective_key == "max_magicka"
    assert magicka.contributions[0].percent_of_reference == 0.08


def test_projection_recognizes_unconditional_all_resource_clause():
    result = ExtremePassiveProjectionService.project(
        _passive(
            "Triune Mind",
            "Increases your Max Health, Magicka, and Stamina by 4%.",
        )
    )
    assert result.status is ExtremePassiveProjectionStatus.REVIEWED_STATIC
    assert {row.objective_key for row in result.contributions} == {
        "max_health",
        "max_magicka",
        "max_stamina",
    }
    assert {row.percent_of_reference for row in result.contributions} == {0.04}


def test_conditional_resource_clause_is_not_flattened_into_static_math():
    result = ExtremePassiveProjectionService.project(
        _passive(
            "Juggernaut",
            "Increases your Max Health by 2% for each piece of Heavy Armor equipped.",
            line="Heavy Armor",
            domain=ExtremeSkillDomain.ARMOR,
        )
    )
    assert result.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED
    assert result.contributions == ()


def test_per_stack_resource_clause_is_contextual_not_static():
    result = ExtremePassiveProjectionService.project(
        _passive(
            "Nothing Wasted",
            "Increases your Max Health by 2% per stack, up to 10 stacks.",
            line="Class Mastery",
        )
    )
    assert result.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED
    assert result.contributions == ()


def test_noncombat_craft_and_utility_passives_are_not_reported_as_unknown_mechanics():
    crafting = ExtremePassiveProjectionService.project(
        _passive(
            "Keen Eye: Ore",
            "Ore in the world will be easier to see when you are 20 meters or closer.",
            line="Blacksmithing",
            domain=ExtremeSkillDomain.CRAFT,
        )
    )
    utility = ExtremePassiveProjectionService.project(
        _passive(
            "Keen Eye: Dig Sites",
            "Dig Sites will be easier to see when you are nearby.",
            line="Excavation",
            domain=ExtremeSkillDomain.UTILITY,
        )
    )
    medicinal_use = ExtremePassiveProjectionService.project(
        _passive(
            "Medicinal Use",
            "When using potions, resulting effects last longer.",
            line="Alchemy",
            domain=ExtremeSkillDomain.CRAFT,
        )
    )

    assert crafting.status is ExtremePassiveProjectionStatus.KNOWN_NONCOMBAT
    assert utility.status is ExtremePassiveProjectionStatus.KNOWN_NONCOMBAT
    assert medicinal_use.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED


def test_resource_passive_audit_classifies_complete_inventory_without_zeroing_unknowns():
    audit = ExtremeResourcePassiveCoverageAuditService(
        universe_service=_Universe(),
        race_repository=_RaceRepository(),
    ).build("max_health")

    assert audit.passives_reviewed == 7
    assert audit.denominator_proven is True
    assert audit.projection_complete is False
    assert any("Last Gasp" in row for row in audit.static_relevant)
    assert any("Tough" in row for row in audit.accounted_elsewhere)
    assert any("Deep Reserves" in row for row in audit.static_irrelevant)
    assert any("Juggernaut" in row for row in audit.context_required)
    assert any("Magicka Controller" in row for row in audit.context_required)
    assert any("Mystery" in row for row in audit.unresolved)


def test_racial_static_resource_requires_matching_canonical_race_stat():
    audit = ExtremeResourcePassiveCoverageAuditService(
        universe_service=_Universe(),
        race_repository=_RaceRepository(),
    ).build("max_magicka")

    assert not any("Tough" in row for row in audit.accounted_elsewhere)
    assert any("Tough" in row for row in audit.static_irrelevant)


def test_resource_passive_audit_rejects_unreviewed_objective():
    try:
        ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme resource passive objective" in str(exc)
    else:
        raise AssertionError("expected unsupported resource passive objective to fail closed")
