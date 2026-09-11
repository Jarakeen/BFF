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


_DESCRIPTIONS = {
    "Blood Magic": (
        "When you hit an enemy with a directly applied Dark Magic ability that has a cost, "
        "the reviewed full-Health branch can temporarily increase the higher of your Max Magicka "
        "or Max Stamina."
    ),
    "Maturation": (
        "When you heal yourself or an ally with a Green Balance ability, grant the healed target "
        "Minor Toughness, increasing their Max Health for the reviewed duration."
    ),
    "Dark Vigor": (
        "For each Shadow ability slotted on the active bar, the reviewed passive increases Max Health."
    ),
}


def _passive(name: str, line: str) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="Test Class",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description=_DESCRIPTIONS[name],
        domain=ExtremeSkillDomain.CLASS,
    )


class _Universe:
    def passives(self):
        return (
            _passive("Blood Magic", "Dark Magic"),
            _passive("Maturation", "Green Balance"),
            _passive("Dark Vigor", "Shadow"),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_objective_specific_class_ownership_only_closes_proven_irrelevant_axes():
    cases = (
        ("Blood Magic", "Dark Magic", "max_health", True),
        ("Blood Magic", "Dark Magic", "max_magicka", False),
        ("Blood Magic", "Dark Magic", "max_stamina", False),
        ("Maturation", "Green Balance", "max_health", False),
        ("Maturation", "Green Balance", "max_magicka", True),
        ("Maturation", "Green Balance", "max_stamina", True),
        ("Dark Vigor", "Shadow", "max_magicka", True),
        ("Dark Vigor", "Shadow", "max_stamina", True),
    )

    for name, line, objective, should_resolve in cases:
        resolution = ExtremeResourceClassPassiveOwnershipService.resolve(
            _passive(name, line),
            objective,
        )
        if should_resolve:
            assert resolution is not None
            row, status = resolution
            assert row.identity == (line, name)
            assert status is ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT
        else:
            assert resolution is None


def test_audit_preserves_only_blood_magic_as_remaining_resource_runtime_blocker():
    audits = {
        objective: ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)
        for objective in ("max_health", "max_magicka", "max_stamina")
    }

    health = audits["max_health"]
    assert "[class] Dark Magic :: Blood Magic" in health.static_irrelevant
    assert "[class] Green Balance :: Maturation" in health.accounted_elsewhere
    assert "[class] Green Balance :: Maturation" not in health.context_required
    assert "[class] Shadow :: Dark Vigor" not in health.context_required
    assert health.context_required == ()
    assert health.unresolved == ()

    for objective in ("max_magicka", "max_stamina"):
        audit = audits[objective]
        assert "[class] Dark Magic :: Blood Magic" in audit.context_required
        assert "[class] Green Balance :: Maturation" in audit.static_irrelevant
        assert "[class] Shadow :: Dark Vigor" in audit.static_irrelevant
        assert audit.unresolved == ()
