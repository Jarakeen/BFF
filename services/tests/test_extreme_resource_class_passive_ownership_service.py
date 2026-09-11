from services.extreme_resource_class_passive_ownership_service import (
    ExtremeResourceClassPassiveOwnershipService,
    ExtremeResourceClassPassiveOwnershipStatus,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, line: str, description: str = "Conditional reviewed mechanic."):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="Warden",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description=description,
        domain=ExtremeSkillDomain.CLASS,
    )


class _Universe:
    def passives(self):
        return (
            _passive(
                "Flourish",
                "Animal Companions",
                "Increases your Magicka and Stamina Recovery for each Animal Companions ability slotted.",
            ),
            _passive(
                "Advanced Species",
                "Animal Companions",
                "Increases your Critical Damage for each Animal Companions ability slotted.",
            ),
            _passive(
                "Frozen Armor",
                "Winter's Embrace",
                "Increases your Physical and Spell Resistance for each Winter's Embrace ability slotted.",
            ),
            _passive(
                "Flourish",
                "Not Animal Companions",
                "Increases your Magicka and Stamina Recovery for each ability slotted.",
            ),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_warden_shared_resolver_rows_are_proven_irrelevant_to_all_max_resources():
    rows = ExtremeResourceClassPassiveOwnershipService.reviewed()
    assert [(row.skill_line, row.passive_name) for row in rows] == [
        ("Animal Companions", "Advanced Species"),
        ("Animal Companions", "Flourish"),
        ("Winter's Embrace", "Frozen Armor"),
    ]
    assert all(
        row.status is ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT
        for row in rows
    )

    for objective in ("max_health", "max_magicka", "max_stamina"):
        for passive in _Universe().passives()[:3]:
            row = ExtremeResourceClassPassiveOwnershipService.resolve(passive, objective)
            assert row is not None
            assert row.status is ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_class_passive_ownership_requires_exact_skill_line_and_class_domain():
    wrong_line = _Universe().passives()[3]
    assert ExtremeResourceClassPassiveOwnershipService.resolve(wrong_line, "max_health") is None

    guild_copy = ExtremePlayerSkillRecord(
        skill_id=2,
        name="Flourish",
        class_type="",
        skill_line="Animal Companions",
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description="Same words, wrong domain.",
        domain=ExtremeSkillDomain.GUILD,
    )
    assert ExtremeResourceClassPassiveOwnershipService.resolve(guild_copy, "max_health") is None


def test_passive_denominator_moves_reviewed_warden_rows_to_static_irrelevant():
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for passive_name in ("Flourish", "Advanced Species", "Frozen Armor"):
            assert any(
                passive_name in row and "Not Animal Companions" not in row
                for row in audit.static_irrelevant
            )
        assert not any("Frozen Armor" in row for row in audit.context_required)
        assert not any("Advanced Species" in row for row in audit.context_required)
        assert any("Not Animal Companions :: Flourish" in row for row in audit.context_required)
