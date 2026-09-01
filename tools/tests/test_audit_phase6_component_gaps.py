from tools.audit_phase6_component_gaps import _disposition, semantic_signals
from tools.audit_skill_component_import_gaps import ImportGapRow


def _gap(*reasons: str) -> ImportGapRow:
    return ImportGapRow(
        skill_rank_id=10,
        coefficient_number=1,
        ability_id=100,
        name="Fixture",
        reasons=tuple(reasons),
        fragment="",
        effect_kind=None,
        damage_type=None,
        is_dot=None,
        is_aoe=None,
    )


def test_semantic_signals_are_candidate_cues_not_ability_specific_rules():
    text = (
        "Deals additional damage when the enemy is below 25% Health. "
        "You also restore 1200 Magicka. This effect has a 20% chance and a cooldown."
    )

    assert semantic_signals(text) == (
        "execute_candidate",
        "resource_event_candidate",
        "secondary_component_candidate",
        "conditional_candidate",
        "temporal_proc_candidate",
    )


def test_semantic_signals_detect_shield_and_healing_wording():
    signals = semantic_signals(
        "Gain a damage shield that absorbs 5000 damage and heal an ally for 2000 Health."
    )

    assert "shield_candidate" in signals
    assert "healing_candidate" in signals


def test_missing_fragment_remains_source_evidence_even_with_ability_context():
    assert _disposition(
        _gap("missing_fragment"),
        ("conditional_candidate",),
        (),
        (),
    ) == "source_evidence"


def test_temporal_proc_signal_is_kept_at_phase7_boundary():
    assert _disposition(
        _gap("effect_kind"),
        ("conditional_candidate", "temporal_proc_candidate"),
        (),
        (),
    ) == "phase7_boundary_candidate"


def test_existing_effect_link_moves_gap_to_richer_semantics():
    assert _disposition(
        _gap("effect_kind"),
        (),
        ("Minor Brittle",),
        (),
    ) == "richer_component_semantics"


def test_plain_unknown_effect_kind_stays_parser_coverage():
    assert _disposition(_gap("effect_kind"), (), (), ()) == "parser_coverage"


def test_plain_shape_gap_stays_classification_field_gap():
    assert _disposition(_gap("target_shape"), (), (), ()) == "classification_field_gap"
