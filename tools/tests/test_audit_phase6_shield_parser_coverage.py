from tools import audit_phase6_shield_parser_coverage as audit
from tools.audit_phase6_heal_shield_unresolved_taxonomy import UnresolvedHealShieldRow


def test_shield_coverage_excludes_modifier_mentions_and_keeps_real_shields(monkeypatch):
    rows = (
        UnresolvedHealShieldRow(
            skill_rank_id=10,
            coefficient_number=1,
            ability_id=100,
            ability_name="Gibbering Example",
            category="other",
            candidate_types=("shield",),
            resolved_effect_kind=None,
            fragment=(
                "Form a damage shield that absorbs 60% of all damage for 10 seconds, "
                "up to a max of $1 damage."
            ),
        ),
        UnresolvedHealShieldRow(
            skill_rank_id=11,
            coefficient_number=1,
            ability_id=101,
            ability_name="Modifier Example",
            category="modifier_mention",
            candidate_types=("heal", "shield"),
            resolved_effect_kind="damage",
            fragment="Reduce healing received and damage shield strength by 12%.",
        ),
    )
    monkeypatch.setattr(audit, "load_unresolved_taxonomy", lambda *args, **kwargs: rows)

    result = audit.load_shield_parser_coverage("ignored.db")

    assert len(result) == 1
    assert result[0].status == "PROVABLE"
    assert result[0].resolved_effect_kind == "shield"
