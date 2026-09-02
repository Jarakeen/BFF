from types import SimpleNamespace

from tools import audit_phase6_closeout as audit
from tools.audit_phase6_component_gaps import Phase6GapRow


def _gap(*, disposition="richer_component_semantics", signals=(), fragment="Deal $1 Flame Damage."):
    return Phase6GapRow(
        skill_rank_id=1,
        coefficient_number=1,
        ability_id=10,
        name="Example",
        phase3_reasons=("effect_kind",),
        disposition=disposition,
        signals=tuple(signals),
        linked_effects=(),
        named_combat_effects=(),
        fragment=fragment,
    )


def _item(gap):
    return SimpleNamespace(gap=gap, is_covered=False)


def test_original_classification_gap_is_cleanup():
    status, reason = audit._closeout_status(_item(_gap(disposition="classification_field_gap")))
    assert status == "CLASSIFICATION_CLEANUP"
    assert "classification-field" in reason


def test_explicit_phase7_disposition_stays_phase7():
    status, _ = audit._closeout_status(_item(_gap(disposition="phase7_boundary_candidate")))
    assert status == "PHASE7_BOUNDARY"


def test_source_evidence_gap_is_blocked_not_cleared():
    status, _ = audit._closeout_status(_item(_gap(disposition="source_evidence")))
    assert status == "SOURCE_EVIDENCE_BLOCKED"


def test_parser_gap_requires_phase6_review():
    status, _ = audit._closeout_status(_item(_gap(disposition="parser_coverage")))
    assert status == "NEEDS_PHASE6_REVIEW"


def test_conditional_multi_damage_is_not_dismissed_as_cleanup():
    gap = _gap(
        signals=("conditional_candidate",),
        fragment="Deal $1 Flame Damage or $2 Flame Damage when the condition is met.",
    )
    status, _ = audit._closeout_status(_item(gap))
    assert status == "NEEDS_PHASE6_REVIEW"


def test_runic_embrace_neighbor_scaling_is_ownership_negative():
    gap = _gap(
        signals=("healing_candidate",),
        fragment="Craft a rune that deals $1 Magic Damage and heals you for $2 Health, scaling off your Max Health.",
    )
    status, reason = audit._closeout_status(_item(gap))
    assert status == "OWNERSHIP_NEGATIVE"
    assert "neighboring heal" in reason


def test_signal_only_multi_heal_is_classification_cleanup():
    gap = _gap(
        signals=("healing_candidate",),
        fragment=(
            "Once summoned, you can activate the twilight matriarch's special ability, "
            "causing it to heal 2 friendly targets for $1 and itself for $2."
        ),
    )
    status, reason = audit._closeout_status(_item(gap))
    assert status == "CLASSIFICATION_CLEANUP"
    assert reason == "multi_heal_classification_gap"


def test_signal_only_attack_triggered_heal_is_phase7_boundary():
    gap = _gap(
        signals=("healing_candidate", "conditional_candidate"),
        fragment=(
            "While transformed, your damaging Light Attacks restore $1 Health and "
            "your fully-charged Heavy Attacks restore $2 Health."
        ),
    )
    status, reason = audit._closeout_status(_item(gap))
    assert status == "PHASE7_BOUNDARY"
    assert reason == "phase7_attack_triggered_heal"


def test_summary_counts_review_rows_separately():
    rows = (
        audit.Phase6CloseoutRow(1, 1, 10, "A", "x", "CLASSIFICATION_CLEANUP", "cleanup", (), ""),
        audit.Phase6CloseoutRow(2, 1, 11, "B", "x", "NEEDS_PHASE6_REVIEW", "review", (), ""),
        audit.Phase6CloseoutRow(3, 1, 12, "C", "x", "PHASE7_BOUNDARY", "later", (), ""),
    )
    summary = audit.summarize(rows)
    assert summary["rows"] == 3
    assert summary["needs_review"] == 1
    assert summary["statuses"]["CLASSIFICATION_CLEANUP"] == 1
    assert summary["review_reasons"]["review"] == 1
