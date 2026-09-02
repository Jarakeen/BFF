from collections import Counter

from tools.audit_phase6_signal_only_semantics import (
    SignalOnlySemanticsRow,
    signal_only_category,
    summarize,
)


def test_attack_triggered_heal_is_phase7_boundary():
    fragment = (
        "While transformed, your damaging Light Attacks restore $1 Health "
        "and your fully-charged Heavy Attacks restore $2 Health."
    )
    assert signal_only_category(fragment, "heal") == "phase7_attack_triggered_heal"


def test_multi_heal_component_is_classification_leftover():
    fragment = "Activate the pet, causing it to heal a friendly target for $3 and itself for $4."
    assert signal_only_category(fragment, "heal") == "multi_heal_classification_gap"


def test_unknown_signal_only_shape_stays_unresolved():
    assert signal_only_category("Special unresolved healing behavior.", "heal") == "unresolved_signal_only"


def test_summarize_counts_signal_only_categories():
    rows = (
        SignalOnlySemanticsRow(1, 1, 10, "A", "phase7_attack_triggered_heal", "heal", "x"),
        SignalOnlySemanticsRow(2, 4, 20, "B", "multi_heal_classification_gap", "heal", "y"),
        SignalOnlySemanticsRow(3, 1, 30, "C", "unresolved_signal_only", None, "z"),
    )
    assert summarize(rows) == Counter(
        {
            "phase7_attack_triggered_heal": 1,
            "multi_heal_classification_gap": 1,
            "unresolved_signal_only": 1,
        }
    )
