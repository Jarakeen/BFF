import json
import sqlite3

from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonIdentityService,
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
        "not found in canonical alchemy Poison tiers" in row
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
