import sqlite3

from tools.audit_phase6_component_gaps import (
    _disposition,
    load_phase6_gap_matrix,
    semantic_signals,
)
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


def test_phase6_signals_stay_scoped_to_component_fragment(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL,
            raw_name TEXT,
            raw_description TEXT,
            raw_tooltip TEXT,
            raw_coef TEXT,
            coef_types TEXT
        );
        CREATE TABLE skill_coefficient (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            type TEXT,
            a REAL,
            b REAL,
            c REAL,
            r REAL,
            avg REAL
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            coef_description TEXT,
            raw_description TEXT,
            raw_tooltip TEXT,
            type1 INTEGER, a1 REAL, b1 REAL, c1 REAL, r1 REAL, avg1 REAL,
            type2 INTEGER, a2 REAL, b2 REAL, c2 REAL, r2 REAL, avg2 REAL,
            type3 INTEGER, a3 REAL, b3 REAL, c3 REAL, r3 REAL, avg3 REAL,
            type4 INTEGER, a4 REAL, b4 REAL, c4 REAL, r4 REAL, avg4 REAL,
            type5 INTEGER, a5 REAL, b5 REAL, c5 REAL, r5 REAL, avg5 REAL,
            type6 INTEGER, a6 REAL, b6 REAL, c6 REAL, r6 REAL, avg6 REAL
        );

        INSERT INTO skill_rank VALUES
            (10, 100, 'Mixed Ability', NULL, NULL, NULL, NULL);
        INSERT INTO ability (
            ability_id, name, coef_description, raw_description,
            type1, a1, b1, c1, r1, avg1,
            type2, a2, b2, c2, r2, avg2
        ) VALUES (
            100,
            'Mixed Ability',
            'Deal $1 Magic Damage to an enemy. Then heal an ally for $2 Health.',
            'Deal damage, then heal an ally.',
            8, .1, 1, 0, 1, 1000,
            8, .1, 1, 0, 1, 1000
        );
        INSERT INTO skill_coefficient VALUES
            (10, 1, '8', .1, 1, 0, 1, 1000),
            (10, 2, '8', .1, 1, 0, 1, 1000);
        """
    )
    db.commit()
    db.close()

    rows = load_phase6_gap_matrix(path)
    damage = next(row for row in rows if row.coefficient_number == 1)

    assert "healing_candidate" not in damage.signals
