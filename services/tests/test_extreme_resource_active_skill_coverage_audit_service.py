from services.extreme_resource_active_skill_coverage_audit_service import (
    ExtremeResourceActiveSkillCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _active(
    name: str,
    description: str,
    *,
    line: str = "Storm Calling",
    domain: ExtremeSkillDomain = ExtremeSkillDomain.CLASS,
    crafted: bool = False,
    skill_id: int = 1,
) -> ExtremePlayerSkillRecord:
    return ExtremePlayerSkillRecord(
        skill_id=skill_id,
        name=name,
        class_type="Sorcerer" if domain is ExtremeSkillDomain.CLASS else "",
        skill_line=line,
        skill_type="Active",
        is_passive=False,
        is_player=True,
        is_crafted=crafted,
        base_ability_id=skill_id,
        max_rank=4,
        max_rank_ability_id=skill_id + 1000,
        description=description,
        domain=domain,
    )


class _Universe:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def actives(self):
        return self.rows


def test_direct_target_max_resource_mutation_remains_relevant():
    row = _active(
        "Resource Morph",
        "While active, increases your Maximum Magicka by 2000.",
    )
    audit = ExtremeResourceActiveSkillCoverageAuditService(
        universe_service=_Universe((row,))
    ).build("max_magicka")

    assert audit.denominator_proven
    assert not audit.projection_complete
    assert audit.proven_irrelevant == ()
    assert len(audit.relevant) == 1
    assert "target maximum resource is directly modified" in audit.relevant[0]


def test_scaling_from_max_resource_is_not_a_resource_mutation():
    row = _active(
        "Scaling Skill",
        "Deals damage based on your Max Magicka and Spell Damage.",
    )
    audit = ExtremeResourceActiveSkillCoverageAuditService(
        universe_service=_Universe((row,))
    ).build("max_magicka")

    assert audit.denominator_proven
    assert audit.projection_complete
    assert len(audit.proven_irrelevant) == 1
    assert audit.relevant == ()
    assert audit.unresolved == ()


def test_toughness_reference_blocks_max_health_pruning():
    row = _active(
        "Toughness Skill",
        "Grants Minor Toughness for 20 seconds.",
    )
    audit = ExtremeResourceActiveSkillCoverageAuditService(
        universe_service=_Universe((row,))
    ).build("max_health")

    assert audit.denominator_proven
    assert not audit.projection_complete
    assert len(audit.relevant) == 1
    assert "Toughness resource modifier reference" in audit.relevant[0]


def test_missing_combat_description_fails_closed_but_known_noncombat_line_does_not():
    combat = _active("Mystery Combat", "", skill_id=10)
    utility = _active(
        "Excavation Utility",
        "",
        line="Excavation",
        domain=ExtremeSkillDomain.UTILITY,
        skill_id=11,
    )
    audit = ExtremeResourceActiveSkillCoverageAuditService(
        universe_service=_Universe((combat, utility))
    ).build("max_stamina")

    assert audit.denominator_proven
    assert not audit.projection_complete
    assert len(audit.proven_irrelevant) == 1
    assert "Excavation Utility" in audit.proven_irrelevant[0]
    assert len(audit.unresolved) == 1
    assert "Mystery Combat" in audit.unresolved[0]


def test_every_active_is_accounted_once_across_the_denominator():
    rows = (
        _active("Irrelevant", "Deals 1000 Flame Damage.", skill_id=20),
        _active("Relevant", "Increase your Max Stamina by 500.", skill_id=21),
        _active("Unknown", "", skill_id=22),
    )
    audit = ExtremeResourceActiveSkillCoverageAuditService(
        universe_service=_Universe(rows)
    ).build("max_stamina")

    assert audit.active_skills_reviewed == 3
    assert audit.denominator_proven
    assert len(audit.proven_irrelevant) == 1
    assert len(audit.relevant) == 1
    assert len(audit.unresolved) == 1
