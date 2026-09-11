from services.extreme_resource_armor_passive_ownership_service import (
    ExtremeResourceArmorPassiveOwnershipService,
    ExtremeResourceArmorPassiveOwnershipStatus,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, line: str, description: str = "Reviewed armor mechanic."):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description=description,
        domain=ExtremeSkillDomain.ARMOR,
    )


class _Universe:
    def passives(self):
        return (
            _passive("Evocation", "Light Armor", "Increases your Magicka Recovery while wearing Light Armor."),
            _passive("Concentration", "Light Armor", "Increases your Physical and Spell Penetration for each piece of Light Armor equipped."),
            _passive("Spell Warding", "Light Armor", "Increases your Spell Resistance for each piece of Light Armor equipped."),
            _passive("Prodigy", "Light Armor", "Increases your Critical Chance for each piece of Light Armor equipped."),
            _passive("Wind Walker", "Medium Armor", "Increases your Stamina Recovery for each piece of Medium Armor equipped."),
            _passive("Agility", "Medium Armor", "Increases your Weapon and Spell Damage for each piece of Medium Armor equipped."),
            _passive("Dexterity", "Medium Armor", "Increases your Critical Damage and Critical Healing for each piece of Medium Armor equipped."),
            _passive("Juggernaut", "Heavy Armor", "Increases your Max Health by 2% for each piece of Heavy Armor equipped."),
            _passive("Evocation", "Not Light Armor", "Increases your Magicka Recovery while wearing armor."),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_shared_armor_resolver_rows_are_exact_and_objective_specific():
    rows = ExtremeResourceArmorPassiveOwnershipService.reviewed()
    assert len(rows) == 8

    for passive in _Universe().passives()[:7]:
        for objective in ("max_health", "max_magicka", "max_stamina"):
            resolved = ExtremeResourceArmorPassiveOwnershipService.resolve(passive, objective)
            assert resolved is not None
            _row, status = resolved
            assert status is ExtremeResourceArmorPassiveOwnershipStatus.PROVEN_IRRELEVANT

    juggernaut = _Universe().passives()[7]
    health = ExtremeResourceArmorPassiveOwnershipService.resolve(juggernaut, "max_health")
    magicka = ExtremeResourceArmorPassiveOwnershipService.resolve(juggernaut, "max_magicka")
    stamina = ExtremeResourceArmorPassiveOwnershipService.resolve(juggernaut, "max_stamina")
    assert health is not None and health[1] is ExtremeResourceArmorPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
    assert magicka is not None and magicka[1] is ExtremeResourceArmorPassiveOwnershipStatus.PROVEN_IRRELEVANT
    assert stamina is not None and stamina[1] is ExtremeResourceArmorPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_armor_passive_ownership_requires_exact_line_and_armor_domain():
    wrong_line = _Universe().passives()[8]
    assert ExtremeResourceArmorPassiveOwnershipService.resolve(wrong_line, "max_health") is None

    class_copy = ExtremePlayerSkillRecord(
        skill_id=2,
        name="Evocation",
        class_type="Test Class",
        skill_line="Light Armor",
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description="Same words, wrong domain.",
        domain=ExtremeSkillDomain.CLASS,
    )
    assert ExtremeResourceArmorPassiveOwnershipService.resolve(class_copy, "max_health") is None


def test_passive_denominator_reconciles_reviewed_armor_effect_families():
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for passive_name in (
            "Evocation",
            "Concentration",
            "Spell Warding",
            "Prodigy",
            "Wind Walker",
            "Agility",
            "Dexterity",
        ):
            assert any(
                passive_name in row and "Not Light Armor" not in row
                for row in audit.static_irrelevant
            )

        if objective == "max_health":
            assert any("Juggernaut" in row for row in audit.accounted_elsewhere)
        else:
            assert any("Juggernaut" in row for row in audit.static_irrelevant)

        assert any("Not Light Armor :: Evocation" in row for row in audit.context_required)
