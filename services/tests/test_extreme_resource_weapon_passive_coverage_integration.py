from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, line: str, description: str):
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
        domain=ExtremeSkillDomain.WEAPON,
    )


class _Universe:
    def passives(self):
        return (
            _passive("Restoration Master", "Restoration Staff", "Increases healing with Restoration Staff spells."),
            _passive("Restoration Expert", "Restoration Staff", "Increases healing on low Health allies."),
            _passive("Essence Drain", "Restoration Staff", "After a fully-charged Heavy Attack, gain Major Mending."),
            _passive("Cycle of Life", "Restoration Staff", "Heavy Attacks restore more Magicka."),
            _passive("Absorb", "Restoration Staff", "Restore Magicka when blocking an attack."),
            _passive("Penetrating Magic", "Destruction Staff", "Destruction Staff abilities ignore Spell Resistance."),
            _passive("Elemental Force", "Destruction Staff", "Increases status effect application chance."),
            _passive("Ancient Knowledge", "Destruction Staff", "Staff element changes ability and block effects."),
            _passive("Tri Focus", "Destruction Staff", "Heavy Attack and Ice Staff block effects."),
            _passive("Destruction Expert", "Destruction Staff", "Restore resources after a kill or shield event."),
            _passive("Deadly Bash", "One Hand and Shield", "Bash deals more damage and costs less Stamina."),
            _passive("Battlefield Mobility", "One Hand and Shield", "Unreviewed movement mechanic."),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_weapon_review_moves_only_exact_proven_rows_to_static_irrelevant():
    reviewed_names = {
        "Restoration Master",
        "Restoration Expert",
        "Essence Drain",
        "Cycle of Life",
        "Absorb",
        "Penetrating Magic",
        "Elemental Force",
        "Ancient Knowledge",
        "Tri Focus",
        "Destruction Expert",
        "Deadly Bash",
    }

    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for passive_name in reviewed_names:
            assert any(passive_name in row for row in audit.static_irrelevant)
            assert not any(passive_name in row for row in audit.context_required)
            assert not any(passive_name in row for row in audit.unresolved)

        assert any("Battlefield Mobility" in row for row in audit.unresolved)
