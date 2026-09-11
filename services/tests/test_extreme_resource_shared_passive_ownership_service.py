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


def _passive(name: str, line: str, domain: ExtremeSkillDomain):
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
        description="Conditional reviewed mechanic.",
        domain=domain,
    )


class _Universe:
    def passives(self):
        return (
            _passive("Slayer", "Fighters Guild", ExtremeSkillDomain.GUILD),
            _passive("Magicka Aid", "Support", ExtremeSkillDomain.ALLIANCE_WAR),
            _passive("Fortress", "One Hand and Shield", ExtremeSkillDomain.WEAPON),
            _passive("Deflect Bolts", "One Hand and Shield", ExtremeSkillDomain.WEAPON),
            _passive("Fortress", "Not One Hand and Shield", ExtremeSkillDomain.WEAPON),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_reviewed_shared_rows_are_proven_irrelevant_to_all_max_resources():
    rows = ExtremeResourceSharedPassiveOwnershipService.reviewed()
    assert [(row.domain.value, row.skill_line, row.passive_name) for row in rows] == [
        ("alliance_war", "Support", "Magicka Aid"),
        ("guild", "Fighters Guild", "Slayer"),
        ("weapon", "One Hand and Shield", "Deflect Bolts"),
        ("weapon", "One Hand and Shield", "Fortress"),
    ]
    assert all(
        row.status is ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT
        for row in rows
    )

    for objective in ("max_health", "max_magicka", "max_stamina"):
        for passive in _Universe().passives()[:4]:
            row = ExtremeResourceSharedPassiveOwnershipService.resolve(passive, objective)
            assert row is not None
            assert row.status is ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_shared_ownership_requires_exact_domain_line_and_name():
    wrong_line = _Universe().passives()[4]
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(wrong_line, "max_health") is None

    wrong_domain = _passive("Slayer", "Fighters Guild", ExtremeSkillDomain.WEAPON)
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(wrong_domain, "max_health") is None


def test_passive_denominator_moves_reviewed_shared_rows_to_static_irrelevant():
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for passive_name in ("Slayer", "Magicka Aid", "Fortress", "Deflect Bolts"):
            assert any(passive_name in row for row in audit.static_irrelevant)
        assert any("Not One Hand and Shield :: Fortress" in row for row in audit.unresolved)
