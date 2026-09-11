from minmax.racial_passive_stat_repository import RacialPassiveResolution
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, description: str):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="",
        skill_line="Test Elf Skills",
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
            _passive("Gift", "Increases your Max Magicka by 2000."),
            _passive("Recovery", "Increases your Magicka Recovery by 258."),
            _passive("Opportunist", "Non-combat racial passive."),
            _passive("Unknown", "Something the racial parser does not understand."),
        )


class _RacialRepository:
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


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_racial_phase5_ownership_preempts_generic_projection_without_hiding_unknowns():
    service = ExtremeResourcePassiveCoverageAuditService(
        universe_service=_Universe(),
        race_repository=_RaceRepository(),
        racial_passive_repository=_RacialRepository(),
    )

    magicka = service.build("max_magicka")
    health = service.build("max_health")

    assert magicka.denominator_proven is True
    assert any("Test Elf Skills :: Gift" in row for row in magicka.accounted_elsewhere)
    assert any("Test Elf Skills :: Recovery" in row for row in magicka.static_irrelevant)
    assert any("Test Elf Skills :: Opportunist" in row for row in magicka.static_irrelevant)
    assert any("Test Elf Skills :: Unknown" in row for row in magicka.unresolved)

    assert any("Test Elf Skills :: Gift" in row for row in health.static_irrelevant)
    assert not any("Test Elf Skills :: Gift" in row for row in health.accounted_elsewhere)
    assert any("Test Elf Skills :: Unknown" in row for row in health.unresolved)
