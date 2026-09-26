import json
import sqlite3

import pytest

from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonIdentityService,
    ExtremeSustainedDPSWeaponPoisonItemEvidence,
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)


def _database(tmp_path, records):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE effect (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE effect_variant (
                id INTEGER PRIMARY KEY,
                effect_id INTEGER NOT NULL,
                type TEXT,
                raw_json TEXT
            );
            """
        )
        for index, (effect_name, tiers) in enumerate(records, start=1):
            db.execute(
                "INSERT INTO effect(id, name) VALUES (?, ?)",
                (index, effect_name),
            )
            db.execute(
                """
                INSERT INTO effect_variant(id, effect_id, type, raw_json)
                VALUES (?, ?, 'Poison', ?)
                """,
                (
                    index,
                    index,
                    json.dumps(
                        {
                            "effect_name": effect_name,
                            "variant": "poison",
                            "tiers": tiers,
                        }
                    ),
                ),
            )
    return path


def _tier(
    name,
    *,
    duration,
    triple_duration=None,
    solvent="Alkahest",
    level=50,
):
    return {
        "kind": "poison",
        "solvent": solvent,
        "level": level,
        "name": name,
        "duration": duration,
        "triple_duration": triple_duration,
    }


def test_poison_name_resolves_every_matching_effect_and_its_duration(tmp_path) -> None:
    path = _database(
        tmp_path,
        (
            ("Ravage Health", (_tier("Test Poison IX", duration=6.4),)),
            ("Maim", (_tier("Test Poison IX", duration=3.5),)),
            ("Cowardice", (_tier("Different Poison IX", duration=3.5),)),
        ),
    )

    result = ExtremeSustainedDPSWeaponPoisonIdentityService(path).resolve(
        "Test Poison IX"
    )

    assert result.resolved is False
    assert result.source_evidence_complete is True
    assert result.exact_selection_proven is False
    assert any("possible effects but not the exact crafted formula" in row for row in result.unresolved)
    assert [
        (row.effect_name, row.base_duration_seconds)
        for row in result.possible_effects
    ] == [
        ("Maim", 3.5),
        ("Ravage Health", 6.4),
    ]
    assert all(row.solvent == "Alkahest" for row in result.possible_effects)
    assert all(row.level == 50 for row in result.possible_effects)


def test_poison_identity_matching_is_case_and_whitespace_insensitive(tmp_path) -> None:
    path = _database(
        tmp_path,
        (
            (
                "Ravage Health",
                (_tier("Damage Health Poison IX", duration=6.4),),
            ),
        ),
    )

    result = ExtremeSustainedDPSWeaponPoisonIdentityService(path).resolve(
        "  damage   health poison IX "
    )

    assert result.resolved is False
    assert result.source_evidence_complete is True
    assert result.poison_id == "damage health poison IX"
    assert result.possible_effects[0].effect_name == "Ravage Health"


def test_missing_poison_name_fails_closed(tmp_path) -> None:
    path = _database(
        tmp_path,
        (("Ravage Health", (_tier("Known Poison IX", duration=6.4),)),),
    )

    result = ExtremeSustainedDPSWeaponPoisonIdentityService(path).resolve(
        "Unknown Poison IX"
    )

    assert result.resolved is False
    assert result.possible_effects == ()
    assert any(
        "not found in canonical alchemy poison tiers" in row.casefold()
        for row in result.unresolved
    )


def test_missing_effect_duration_fails_closed(tmp_path) -> None:
    path = _database(
        tmp_path,
        (("Ravage Health", (_tier("Broken Poison IX", duration=None),)),),
    )

    result = ExtremeSustainedDPSWeaponPoisonIdentityService(path).resolve(
        "Broken Poison IX"
    )

    assert result.resolved is False
    assert any(
        "has no valid duration" in row
        for row in result.unresolved
    )


def test_conflicting_duplicate_effect_rows_fail_closed(tmp_path) -> None:
    path = _database(
        tmp_path,
        (
            ("Ravage Health", (_tier("Conflict Poison IX", duration=6.4),)),
            ("Ravage Health", (_tier("Conflict Poison IX", duration=7.0),)),
        ),
    )

    result = ExtremeSustainedDPSWeaponPoisonIdentityService(path).resolve(
        "Conflict Poison IX"
    )

    assert result.resolved is False
    assert any(
        "conflicting imported poison tier evidence" in row
        for row in result.unresolved
    )


def test_generated_formula_identity_is_not_treated_as_saved_item_label(tmp_path) -> None:
    path = _database(
        tmp_path,
        (("Ravage Health", (_tier("Damage Health Poison IX", duration=6.4),)),),
    )

    formula_id = "alchemy_formula:u50:a+b:ravage_health"
    result = ExtremeSustainedDPSWeaponPoisonIdentityService(path).resolve(formula_id)

    assert result.resolved is False
    assert result.possible_effects == ()
    assert result.source_evidence_complete is False
    assert any(
        "generated formula identity is not a crafted poison item-label witness" in row
        for row in result.unresolved
    )


@pytest.mark.parametrize("duration", (-1.0, float("inf"), float("nan")))
def test_poison_possible_effect_rejects_invalid_base_duration(duration) -> None:
    with pytest.raises(ValueError, match="base duration must be finite and non-negative"):
        ExtremeSustainedDPSWeaponPoisonPossibleEffect(
            effect_name="Breach",
            base_duration_seconds=duration,
        )


def test_poison_possible_effect_normalizes_text_fields() -> None:
    effect = ExtremeSustainedDPSWeaponPoisonPossibleEffect(
        effect_name="  Minor   Breach ",
        base_duration_seconds=10,
        triple_duration_seconds=5,
        solvent="  Alkahest   ",
        level=50,
    )

    assert effect.effect_name == "Minor Breach"
    assert effect.solvent == "Alkahest"
    assert effect.base_duration_seconds == 10.0
    assert effect.triple_duration_seconds == 5.0


def test_poison_item_evidence_rejects_exact_selection_without_complete_source() -> None:
    with pytest.raises(
        ValueError,
        match="cannot be proven without complete source evidence",
    ):
        ExtremeSustainedDPSWeaponPoisonItemEvidence(
            poison_id="Test Poison IX",
            possible_effects=(),
            source_evidence_complete=False,
            exact_selection_proven=True,
        )


def test_poison_item_evidence_normalizes_and_deduplicates_diagnostics() -> None:
    result = ExtremeSustainedDPSWeaponPoisonItemEvidence(
        poison_id="  Test   Poison IX ",
        possible_effects=(),
        source_evidence_complete=False,
        exact_selection_proven=False,
        evidence=(" source ", "source", ""),
        unresolved=(" missing ", "missing", ""),
    )

    assert result.poison_id == "Test Poison IX"
    assert result.evidence == ("source",)
    assert result.unresolved == ("missing",)


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("effect_name", 7, "effect_name must be a string"),
        ("base_duration_seconds", "10", "base duration must be numeric"),
        ("triple_duration_seconds", "5", "triple duration must be numeric"),
        ("solvent", 7, "solvent must be a string or None"),
    ),
)
def test_poison_possible_effect_rejects_coerced_fields(field, value, match) -> None:
    kwargs = {
        "effect_name": "Minor Breach",
        "base_duration_seconds": 10.0,
        "triple_duration_seconds": 5.0,
        "solvent": "Alkahest",
        "level": 50,
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=match):
        ExtremeSustainedDPSWeaponPoisonPossibleEffect(**kwargs)


def test_poison_item_evidence_requires_tuple_string_diagnostics() -> None:
    with pytest.raises(TypeError, match="possible_effects must be a tuple"):
        ExtremeSustainedDPSWeaponPoisonItemEvidence(
            poison_id="Test Poison IX",
            possible_effects=[],  # type: ignore[arg-type]
            source_evidence_complete=False,
            exact_selection_proven=False,
        )

    with pytest.raises(TypeError, match="evidence must be a tuple"):
        ExtremeSustainedDPSWeaponPoisonItemEvidence(
            poison_id="Test Poison IX",
            possible_effects=(),
            source_evidence_complete=False,
            exact_selection_proven=False,
            evidence=["source"],  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="unresolved must contain only strings"):
        ExtremeSustainedDPSWeaponPoisonItemEvidence(
            poison_id="Test Poison IX",
            possible_effects=(),
            source_evidence_complete=False,
            exact_selection_proven=False,
            unresolved=("gap", 7),  # type: ignore[arg-type]
        )


def test_poison_identity_resolver_requires_string_poison_id(tmp_path) -> None:
    path = _database(tmp_path, ())

    with pytest.raises(TypeError, match="poison_id must be a string"):
        ExtremeSustainedDPSWeaponPoisonIdentityService(path).resolve(7)  # type: ignore[arg-type]
