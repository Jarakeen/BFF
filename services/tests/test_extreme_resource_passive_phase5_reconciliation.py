from types import SimpleNamespace

from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _racial(name: str, line: str, description: str) -> ExtremePlayerSkillRecord:
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
        max_rank=3,
        max_rank_ability_id=None,
        description=description,
        domain=ExtremeSkillDomain.RACIAL,
    )


class _Universe:
    def passives(self):
        return (
            _racial(
                "Syrabane's Boon",
                "High Elf Skills",
                "Increases your Max Magicka by 2000.",
            ),
            _racial(
                "Spell Recharge",
                "High Elf Skills",
                "When you activate an ability, restore resources.",
            ),
            _racial(
                "Resist Affliction",
                "Wood Elf Skills",
                "Increases your Max Stamina by 2000.",
            ),
            _racial(
                "Hunter's Eye",
                "Wood Elf Skills",
                "Increases movement speed after Roll Dodge.",
            ),
        )


class _EmptyRaceRepository:
    def get_stat_map_by_name(self, name):
        return {}


class _Phase5RacialRepository:
    def resolve(self, race_name, progression):
        stats = {}
        if race_name == "High Elf" and progression.passive_rank("Syrabane's Boon") == 3:
            stats["max_magicka"] = 2000.0
        if race_name == "Wood Elf" and progression.passive_rank("Resist Affliction") == 3:
            stats["max_stamina"] = 2000.0
        return SimpleNamespace(stats=stats, boundaries=(), unresolved=())


def _service():
    return ExtremeResourcePassiveCoverageAuditService(
        universe_service=_Universe(),
        race_repository=_EmptyRaceRepository(),
        racial_passive_repository=_Phase5RacialRepository(),
    )


def test_phase5_racial_resolver_reconciles_magicka_without_race_stat_fallback():
    audit = _service().build("max_magicka")

    assert audit.static_relevant == ()
    assert any("Syrabane's Boon" in row for row in audit.accounted_elsewhere)


def test_phase5_racial_resolver_reconciles_stamina_without_race_stat_fallback():
    audit = _service().build("max_stamina")

    assert audit.static_relevant == ()
    assert any("Resist Affliction" in row for row in audit.accounted_elsewhere)
