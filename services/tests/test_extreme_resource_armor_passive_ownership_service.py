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


_REVIEWED_NON_RESOURCE = (
    ("Light Armor Bonuses", "Light Armor"),
    ("Light Armor Penalties", "Light Armor"),
    ("Evocation", "Light Armor"),
    ("Concentration", "Light Armor"),
    ("Spell Warding", "Light Armor"),
    ("Prodigy", "Light Armor"),
    ("Wind Walker", "Medium Armor"),
    ("Agility", "Medium Armor"),
    ("Dexterity", "Medium Armor"),
    ("Heavy Armor Bonuses", "Heavy Armor"),
    ("Heavy Armor Penalties", "Heavy Armor"),
)


class _Universe:
    def passives(self):
        return tuple(_passive(name, line) for name, line in _REVIEWED_NON_RESOURCE) + (
            _passive(
                "Juggernaut",
                "Heavy Armor",
                "Increases your Max Health by 2% for each piece of Heavy Armor equipped.",
            ),
            _passive(
                "Evocation",
                "Not Light Armor",
                "Increases your Magicka Recovery while wearing armor.",
            ),
            _passive(
                "Heavy Armor Bonuses",
                "Not Heavy Armor",
                "Same name, wrong armor line.",
            ),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_reviewed_armor_rows_are_exact_and_objective_specific():
    rows = ExtremeResourceArmorPassiveOwnershipService.reviewed()
    assert len(rows) == 12

    for passive_name, skill_line in _REVIEWED_NON_RESOURCE:
        passive = _passive(passive_name, skill_line)
        for objective in ("max_health", "max_magicka", "max_stamina"):
            resolved = ExtremeResourceArmorPassiveOwnershipService.resolve(passive, objective)
            assert resolved is not None
            _row, status = resolved
            assert status is ExtremeResourceArmorPassiveOwnershipStatus.PROVEN_IRRELEVANT

    juggernaut = _passive("Juggernaut", "Heavy Armor")
    health = ExtremeResourceArmorPassiveOwnershipService.resolve(juggernaut, "max_health")
    magicka = ExtremeResourceArmorPassiveOwnershipService.resolve(juggernaut, "max_magicka")
    stamina = ExtremeResourceArmorPassiveOwnershipService.resolve(juggernaut, "max_stamina")
    assert health is not None and health[1] is ExtremeResourceArmorPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
    assert magicka is not None and magicka[1] is ExtremeResourceArmorPassiveOwnershipStatus.PROVEN_IRRELEVANT
    assert stamina is not None and stamina[1] is ExtremeResourceArmorPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_armor_passive_ownership_requires_exact_line_and_armor_domain():
    wrong_line = _passive("Evocation", "Not Light Armor")
    assert ExtremeResourceArmorPassiveOwnershipService.resolve(wrong_line, "max_health") is None

    wrong_summary_line = _passive("Heavy Armor Bonuses", "Not Heavy Armor")
    assert ExtremeResourceArmorPassiveOwnershipService.resolve(wrong_summary_line, "max_health") is None

    class_copy = ExtremePlayerSkillRecord(
        skill_id=2,
        name="Light Armor Bonuses",
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
    reviewed_identities = tuple(
        f"[armor] {line} :: {name}"
        for name, line in _REVIEWED_NON_RESOURCE
    )
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for identity in reviewed_identities:
            assert identity in audit.static_irrelevant
            assert identity not in audit.context_required
            assert identity not in audit.unresolved

        if objective == "max_health":
            assert "[armor] Heavy Armor :: Juggernaut" in audit.accounted_elsewhere
        else:
            assert "[armor] Heavy Armor :: Juggernaut" in audit.static_irrelevant

        assert "[armor] Not Light Armor :: Evocation" in audit.context_required
        assert "[armor] Not Heavy Armor :: Heavy Armor Bonuses" in audit.unresolved
