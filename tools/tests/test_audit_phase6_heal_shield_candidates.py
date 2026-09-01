from tools.audit_phase6_heal_shield_candidates import summarize
from tools.audit_phase6_heal_shield_candidates import HealShieldCandidateRow


def test_summary_counts_provable_and_unresolved_rows():
    rows = (
        HealShieldCandidateRow(
            skill_rank_id=1,
            coefficient_number=1,
            ability_id=10,
            ability_name="Heal Fixture",
            candidate_types=("heal",),
            resolved_effect_kind="heal",
            status="PROVABLE",
            phase3_reasons=("effect_kind",),
            fragment="Heal for $1 Health.",
        ),
        HealShieldCandidateRow(
            skill_rank_id=2,
            coefficient_number=1,
            ability_id=20,
            ability_name="Shield Fixture",
            candidate_types=("shield",),
            resolved_effect_kind=None,
            status="UNRESOLVED",
            phase3_reasons=("effect_kind",),
            fragment="Gain a shield after the effect ends.",
        ),
    )

    result = summarize(rows)

    assert result["candidates"] == 2
    assert result["provable"] == 1
    assert result["unresolved"] == 1
    assert result["candidate_counts"]["heal"] == 1
    assert result["candidate_counts"]["shield"] == 1
    assert result["provable_counts"]["heal"] == 1
