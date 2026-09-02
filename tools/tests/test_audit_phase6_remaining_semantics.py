from tools import audit_phase6_remaining_semantics as audit
from tools.audit_phase6_component_gaps import Phase6GapRow


class _FakeRepository:
    def __init__(self, path, covered=()):
        self.covered = set(covered)

    def resolve(self, skill_rank_id, coefficient_number):
        return (object(),) if (skill_rank_id, coefficient_number) in self.covered else ()


def _row(rank, coef, *, signals=(), disposition="richer_component_semantics"):
    return Phase6GapRow(
        skill_rank_id=rank,
        coefficient_number=coef,
        ability_id=1000 + rank,
        name=f"Ability {rank}",
        phase3_reasons=("effect_kind",),
        disposition=disposition,
        signals=signals,
        linked_effects=(),
        named_combat_effects=(),
        fragment="example",
    )


def test_remaining_semantics_reconciles_canonical_phase6_coverage(monkeypatch):
    gaps = (
        _row(10, 1, signals=("resource_event_candidate",)),
        _row(20, 2, signals=("secondary_component_candidate",)),
        _row(30, 1, signals=("conditional_candidate",)),
        _row(40, 1, signals=("secondary_component_candidate",)),
        _row(50, 2, signals=("conditional_candidate",)),
        _row(60, 1),
        _row(70, 1, signals=("conditional_candidate",)),
        _row(80, 1, disposition="parser_coverage"),
        _row(90, 2, disposition="parser_coverage"),
        _row(100, 2, disposition="source_evidence"),
    )
    monkeypatch.setattr(audit, "load_phase6_gap_matrix", lambda *args, **kwargs: gaps)

    monkeypatch.setattr(
        audit,
        "SkillComponentResourceEventRepository",
        lambda path: _FakeRepository(path, {(10, 1)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentEffectRelationshipRepository",
        lambda path: _FakeRepository(path),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentConditionRepository",
        lambda path: _FakeRepository(path),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentConditionalConsequenceRepository",
        lambda path: _FakeRepository(path, {(30, 1)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentCurrentBonusRepository",
        lambda path: _FakeRepository(path, {(80, 1)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentDamageScalingRepository",
        lambda path: _FakeRepository(path, {(50, 2)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentResourceRestoreDisplayRepository",
        lambda path: _FakeRepository(path, {(90, 2)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentRoleRepository",
        lambda path: _FakeRepository(path, {(20, 2)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentSecondaryHealingRepository",
        lambda path: _FakeRepository(path),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentMissingHealthHealingRepository",
        lambda path: _FakeRepository(path),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentSourceStatRuleRepository",
        lambda path: _FakeRepository(path, {(100, 2)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentStatScalingRepository",
        lambda path: _FakeRepository(path, {(60, 1)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentTriggerRelationshipRepository",
        lambda path: _FakeRepository(path, {(70, 1)}),
    )
    monkeypatch.setattr(
        audit,
        "SkillComponentUtilityEffectRepository",
        lambda path: _FakeRepository(path, {(40, 1)}),
    )

    rows = audit.load_remaining_phase6_semantics("ignored.db")
    summary = audit.summarize(rows)

    assert summary["rows"] == 10
    assert summary["covered"] == 10
    assert summary["remaining"] == 0
    assert rows[0].covered_by == ("resource_event",)
    assert rows[1].covered_by == ("component_role",)
    assert rows[2].covered_by == ("conditional_consequence",)
    assert rows[3].covered_by == ("utility_effect",)
    assert rows[4].covered_by == ("damage_scaling",)
    assert rows[5].covered_by == ("stat_scaling",)
    assert rows[6].covered_by == ("component_trigger",)
    assert rows[7].covered_by == ("current_stat_bonus_display",)
    assert rows[8].covered_by == ("resource_restore_display",)
    assert rows[9].covered_by == ("source_mapped_stat_rule",)
    assert summary["signals"]["secondary_component_candidate"] == 0
