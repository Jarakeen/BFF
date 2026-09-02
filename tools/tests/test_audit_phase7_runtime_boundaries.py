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

    assert concerns == ("trigger_detection", "trigger_count", "stack_state", "stack_threshold")


def test_flame_lash_reactivation_requires_trigger_resolution_and_stack_state():
    concerns = audit.classify_runtime_concerns(
        _row("Activating again consumes a stack to deal $1 Flame Damage and heal for $2 Health.")
    )

    assert concerns == ("trigger_resolution", "stack_state")


def test_burning_light_stack_threshold_is_explicit_without_inventing_trigger_identity():
    concerns = audit.classify_runtime_concerns(
        _row("After reaching 4 stacks, you deal $1 Magic Damage to your target.")
    )

    assert concerns == (
        "trigger_resolution",
        "stack_state",
        "stack_threshold",
    )


def test_static_reverberation_separates_chance_cooldown_and_cadence():
    concerns = audit.classify_runtime_concerns(
        _row("When you deal damage, you have a 5% chance to deal $1 Shock Damage, up to once every 0.3 seconds.")
    )

    assert concerns == (
        "trigger_resolution",
        "chance",
        "cooldown",
        "cadence",
    )


def test_plain_once_every_is_cadence_not_cooldown():
    concerns = audit.classify_runtime_concerns(
        _row("The direwolf deals $1 Physical Damage once every 2 seconds.")
    )

    assert concerns == ("cadence",)


def test_explicit_cooldown_wording_is_cooldown():
    concerns = audit.classify_runtime_concerns(
        _row("This effect has a 10 second cooldown.")
    )

    assert concerns == ("cooldown",)


def test_crystal_fragments_tracks_chance_and_persistent_next_cast_state():
    concerns = audit.classify_runtime_concerns(
        _row(
            "While slotted on either bar, casting a non-Ultimate ability has a 33% chance "
            "of causing your next Crystal Fragments to be instant cast at half cost."
        )
    )

    assert concerns == (
        "trigger_resolution",
        "chance",
        "state_window",
    )


def test_bound_armaments_keeps_stack_state_separate_from_cadence():
    concerns = audit.classify_runtime_concerns(
        _row(
            "When at one or more stacks, you can arm up to 4 of them to strike your target "
            "for $1 Physical Damage every 0.3 seconds for each stack consumed."
        )
    )

    assert concerns == (
        "stack_state",
        "cadence",
    )


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
            ("trigger_resolution", "chance"),
            "later",
            (),
            "",
        ),
    )

    summary = audit.summarize(rows)

    assert summary["rows"] == 3
    assert summary["without_canonical_trigger"] == 2
    assert summary["trigger_resolution"] == 1
    assert summary["runtime_review"] == 0
    assert summary["concerns"]["trigger_detection"] == 1
    assert summary["concerns"]["cadence"] == 1
    assert summary["concerns"]["chance"] == 1
    assert summary["triggers"]["light_attack"] == 1
