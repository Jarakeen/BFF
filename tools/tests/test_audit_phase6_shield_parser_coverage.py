from minmax.skill_component_text_evidence import SkillComponentTextEvidence
from tools import audit_phase6_shield_parser_coverage as audit
from tools.audit_skill_component_text_semantics import ComponentSemanticAuditRow


def _row(*, rank, ability, name, kind, fragment):
    return ComponentSemanticAuditRow(
        skill_rank_id=rank,
        ability_id=ability,
        name=name,
        coefficient_number=1,
        coefficient_type="1",
        active_coefficient=True,
        raw_slot_matches=True,
        text=SkillComponentTextEvidence(
            coefficient_number=1,
            fragment=fragment,
            effect_kind=kind,
        ),
    )


def test_shield_coverage_uses_stable_active_corpus_and_excludes_modifiers(monkeypatch):
    rows = (
        _row(
            rank=10,
            ability=100,
            name="Gibbering Example",
            kind="shield",
            fragment=(
                "Form a damage shield that absorbs 60% of all damage for 10 seconds, "
                "up to a max of $1 damage."
            ),
        ),
        _row(
            rank=11,
            ability=101,
            name="Modifier Example",
            kind="damage",
            fragment="Deal $1 Flame Damage and reduce damage shield strength by 12%.",
        ),
        _row(
            rank=12,
            ability=102,
            name="Neighboring Shield Example",
            kind="damage",
            fragment=(
                "Deal $1 Magic Damage and gain a damage shield that absorbs up to $2 damage."
            ),
        ),
    )
    monkeypatch.setattr(audit, "build_semantic_audit", lambda *args, **kwargs: rows)

    result = audit.load_shield_parser_coverage("ignored.db")

    assert len(result) == 2
    assert result[0].status == "PROVABLE"
    assert result[0].resolved_effect_kind == "shield"
    assert result[1].status == "NON_SHIELD_COMPONENT"
    assert result[1].resolved_effect_kind == "damage"
