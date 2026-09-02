from tools import audit_phase7_runtime_boundaries as audit
from tools.audit_phase6_closeout import Phase6CloseoutRow
from minmax.skill_component_trigger_relationship import SkillComponentTriggerType


def _row(fragment: str) -> Phase6CloseoutRow:
    return Phase6CloseoutRow(
        skill_rank_id=1,
        coefficient_number=1,
        ability_id=10,
        ability_name="Example",
        disposition="phase7_boundary_candidate",
        closeout_status="PHASE7_BOUNDARY",
        reason="later",
        signals=(),
        fragment=fragment,
    )


def test_attack_trigger_is_runtime_event_not_new_effect_identity():
    concerns = audit.classify_runtime_concerns(
        _row("Light Attacks deal $1 damage."),
        (SkillComponentTriggerType.LIGHT_ATTACK,),
    )

    assert concerns == ("trigger_detection", "attack_event")


def test_effect_end_trigger_records_lifecycle_work():
    concerns = audit.classify_runtime_concerns(
        _row("When the effect ends, deal $1 damage."),
        (SkillComponentTriggerType.EFFECT_ENDED,),
    )

    assert concerns == ("trigger_detection", "effect_lifecycle")


def test_delay_cadence_duration_and_state_are_separate_runtime_concerns():
    row = _row(
        "While the field grows, after 1 second it pulses every 2 seconds for 6 seconds."
    )

    concerns = audit.classify_runtime_concerns(row)

    assert concerns == ("delay", "cadence", "duration_window", "state_window")


def test_charge_threshold_keeps_trigger_count_separate_from_detection():
    concerns = audit.classify_runtime_concerns(
        _row("When you reach 3 charges, deal $1 damage."),
        (SkillComponentTriggerType.CHARGE_THRESHOLD_REACHED,),
    )

    assert concerns == ("trigger_detection", "trigger_count")


def test_unrecognized_phase7_boundary_stays_explicit_runtime_review():
    concerns = audit.classify_runtime_concerns(_row("Unclassified temporal wording for $1."))

    assert concerns == ("runtime_review",)


def test_summary_counts_rows_concerns_and_missing_trigger_relationships():
    rows = (
        audit.Phase7RuntimeBoundaryRow(
            1,
            1,
            10,
            "A",
            (SkillComponentTriggerType.LIGHT_ATTACK,),
            ("trigger_detection", "attack_event"),
            "later",
            (),
            "",
        ),
        audit.Phase7RuntimeBoundaryRow(
            2,
            1,
            20,
            "B",
            (),
            ("cadence",),
            "later",
            (),
            "",
        ),
        audit.Phase7RuntimeBoundaryRow(
            3,
            1,
            30,
            "C",
            (),
            ("runtime_review",),
            "later",
            (),
            "",
        ),
    )

    summary = audit.summarize(rows)

    assert summary["rows"] == 3
    assert summary["without_canonical_trigger"] == 2
    assert summary["runtime_review"] == 1
    assert summary["concerns"]["trigger_detection"] == 1
    assert summary["concerns"]["cadence"] == 1
    assert summary["triggers"]["light_attack"] == 1
