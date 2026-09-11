from minmax.racial_passive_stat_repository import RacialPassiveResolution
from services.extreme_resource_racial_passive_ownership_service import (
    ExtremeResourceRacialPassiveOwnershipService,
    ExtremeResourceRacialPassiveOwnershipStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, line: str = "Test Elf Skills", *, max_rank: int = 3):
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
        max_rank=max_rank,
        max_rank_ability_id=None,
        description="Canonical racial passive.",
        domain=ExtremeSkillDomain.RACIAL,
    )


class _Repository:
    def resolve(self, race_name, progression):
        assert race_name == "Test Elf"
        ranks = progression.passive_ranks or {}
        if ranks.get("Gift") == 3:
            return RacialPassiveResolution(stats={"max_magicka": 2000.0})
        if ranks.get("Recovery") == 3:
            return RacialPassiveResolution(stats={"magicka_recovery": 258.0})
        if ranks.get("Opportunist") == 3:
            return RacialPassiveResolution(
                stats={},
                boundaries=("Non-combat racial passive outside combat capability audit: Opportunist",),
            )
        if ranks.get("Unknown") == 3:
            return RacialPassiveResolution(
                stats={},
                unresolved=("Racial passive tooltip is not yet stat-mapped: Unknown",),
            )
        return RacialPassiveResolution(stats={})


def test_racial_resource_contributor_is_canonically_accounted_only_for_matching_objective():
    passives = (_passive("Gift"), _passive("Recovery"), _passive("Opportunist"))
    service = ExtremeResourceRacialPassiveOwnershipService(_Repository())

    magicka = service.resolve(passives[0], "max_magicka", passives)
    health = service.resolve(passives[0], "max_health", passives)

    assert magicka is not None
    assert magicka.status is ExtremeResourceRacialPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
    assert magicka.resolved_stats == ("max_magicka",)

    assert health is not None
    assert health.status is ExtremeResourceRacialPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_clean_non_resource_and_noncombat_racial_rows_are_proven_irrelevant():
    passives = (_passive("Gift"), _passive("Recovery"), _passive("Opportunist"))
    service = ExtremeResourceRacialPassiveOwnershipService(_Repository())

    recovery = service.resolve(passives[1], "max_magicka", passives)
    opportunist = service.resolve(passives[2], "max_health", passives)

    assert recovery is not None
    assert recovery.status is ExtremeResourceRacialPassiveOwnershipStatus.PROVEN_IRRELEVANT
    assert recovery.resolved_stats == ("magicka_recovery",)

    assert opportunist is not None
    assert opportunist.status is ExtremeResourceRacialPassiveOwnershipStatus.PROVEN_IRRELEVANT
    assert opportunist.boundaries


def test_unmapped_or_wrong_domain_racial_rows_fail_closed():
    passives = (_passive("Unknown"),)
    service = ExtremeResourceRacialPassiveOwnershipService(_Repository())

    assert service.resolve(passives[0], "max_health", passives) is None

    wrong_domain = ExtremePlayerSkillRecord(
        skill_id=2,
        name="Gift",
        class_type="",
        skill_line="Test Elf Skills",
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=3,
        max_rank_ability_id=None,
        description="Same name, wrong domain.",
        domain=ExtremeSkillDomain.CLASS,
    )
    assert service.resolve(wrong_domain, "max_magicka", (wrong_domain,)) is None
