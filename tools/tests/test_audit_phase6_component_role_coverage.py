from collections import Counter

from tools.audit_phase6_component_role_coverage import ComponentRoleCoverageRow, summarize


def _row(category: str, roles=("additional_damage",)):
    return ComponentRoleCoverageRow(
        skill_rank_id=1,
        coefficient_number=2,
        ability_id=10,
        ability_name="Example",
        disposition="richer_component_semantics",
        signals=("secondary_component_candidate",),
        audit_category=category,
        repository_roles=roles,
        fragment="example",
    )


def test_component_role_coverage_distinguishes_extra_repository_matches():
    rows = (
        _row("explicit_additional_damage"),
        _row("classification_leftover", ("additional_heal",)),
    )

    summary = summarize(rows)

    assert summary["resolved"] == 2
    assert summary["statuses"] == Counter({"AUDITED_CANDIDATE": 1, "EXTRA_REPOSITORY_MATCH": 1})
    assert summary["roles"] == Counter({"additional_damage": 1, "additional_heal": 1})
    assert summary["extra_categories"] == Counter({"classification_leftover": 1})
