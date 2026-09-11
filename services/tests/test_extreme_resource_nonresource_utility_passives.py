from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_resource_shared_passive_ownership_service import (
    ExtremeResourceSharedPassiveOwnershipService,
    ExtremeResourceSharedPassiveOwnershipStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


_REVIEWED = (
    (ExtremeSkillDomain.ALLIANCE_WAR, "Support", "Battle Resurrection"),
    (ExtremeSkillDomain.ALLIANCE_WAR, "Support", "Combat Medic"),
    (ExtremeSkillDomain.CRAFT, "Alchemy", "Chemistry"),
    (ExtremeSkillDomain.CRAFT, "Alchemy", "Laboratory Use"),
    (ExtremeSkillDomain.CRAFT, "Alchemy", "Medicinal Use"),
    (ExtremeSkillDomain.CRAFT, "Alchemy", "Snakeblood"),
    (ExtremeSkillDomain.CRAFT, "Alchemy", "Solvent Proficiency"),
    (ExtremeSkillDomain.CRAFT, "Provisioning", "Brewer"),
    (ExtremeSkillDomain.CRAFT, "Provisioning", "Chef"),
    (ExtremeSkillDomain.CRAFT, "Provisioning", "Connoisseur"),
    (ExtremeSkillDomain.CRAFT, "Provisioning", "Gourmand"),
)


def _passive(domain: ExtremeSkillDomain, line: str, name: str) -> ExtremePlayerSkillRecord:
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
        description="Reviewed utility mechanic.",
        domain=domain,
    )


class _Universe:
    def passives(self):
        return tuple(_passive(domain, line, name) for domain, line, name in _REVIEWED)


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_nonresource_utility_passives_are_proven_irrelevant_to_resource_maxima():
    for objective in ("max_health", "max_magicka", "max_stamina"):
        for domain, line, name in _REVIEWED:
            row = ExtremeResourceSharedPassiveOwnershipService.resolve(
                _passive(domain, line, name),
                objective,
            )
            assert row is not None
            assert row.status is ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_nonresource_utility_passives_leave_context_required_bucket():
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        assert audit.context_required == ()
        assert audit.unresolved == ()
        assert len(audit.static_irrelevant) == len(_REVIEWED)
