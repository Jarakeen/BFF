import json
import sqlite3

from minmax.weapon_poison_availability_repository import (
    WeaponPoisonAvailabilityRepository,
)


def _database(tmp_path):
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
    return path


def _insert_variant(
    path,
    *,
    effect_id,
    effect_name,
    variant_type,
    formulas,
    variant=None,
):
    payload = {
        "source": "UESP",
        "source_kind": "alchemy_effect_page",
        "effect_name": effect_name,
        "variant": variant or variant_type.casefold(),
        "formulas": formulas,
        "source_files": [f"{effect_name.casefold().replace(' ', '_')}.html"],
    }
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT OR IGNORE INTO effect(id, name) VALUES (?, ?)",
            (effect_id, effect_name),
        )
        db.execute(
            """
            INSERT INTO effect_variant(id, effect_id, type, raw_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                effect_id * 10 + (1 if variant_type == "Poison" else 2),
                effect_id,
                variant_type,
                json.dumps(payload),
            ),
        )


def _formula(*traits):
    return {
        "ingredients": ["Reagent A", "Reagent B", "Reagent C"],
        "effects": list(traits),
    }


def test_catalog_uses_only_poison_variants(tmp_path) -> None:
    path = _database(tmp_path)
    _insert_variant(
        path,
        effect_id=1,
        effect_name="Breach",
        variant_type="Poison",
        formulas=(_formula("Breach", "Protection"),),
    )
    _insert_variant(
        path,
        effect_id=2,
        effect_name="Restore Health",
        variant_type="Potion",
        formulas=(_formula("Restore Health"),),
    )

    result = WeaponPoisonAvailabilityRepository(path).catalog()

    assert result.unresolved == ()
    assert len(result.formulas) == 1
    assert set(result.formulas[0].traits) == {"Breach", "Protection"}


def test_poison_formula_duplicates_across_effect_pages_merge_by_canonical_formula(tmp_path) -> None:
    path = _database(tmp_path)
    formula = _formula("Breach", "Protection")
    _insert_variant(
        path,
        effect_id=1,
        effect_name="Breach",
        variant_type="Poison",
        formulas=(formula,),
    )
    _insert_variant(
        path,
        effect_id=2,
        effect_name="Protection",
        variant_type="Poison",
        formulas=(formula,),
    )

    result = WeaponPoisonAvailabilityRepository(path).catalog()

    assert result.unresolved == ()
    assert len(result.formulas) == 1
    assert set(result.formulas[0].source_effects) == {"Breach", "Protection"}


def test_missing_poison_formula_payloads_fail_closed(tmp_path) -> None:
    path = _database(tmp_path)
    _insert_variant(
        path,
        effect_id=1,
        effect_name="Breach",
        variant_type="Poison",
        formulas=(),
    )

    result = WeaponPoisonAvailabilityRepository(path).catalog()

    assert result.formulas == ()
    assert any(
        "contains no reusable Poison formula payloads" in row
        for row in result.unresolved
    )


def test_wrong_variant_marker_in_poison_row_is_rejected(tmp_path) -> None:
    path = _database(tmp_path)
    _insert_variant(
        path,
        effect_id=1,
        effect_name="Breach",
        variant_type="Poison",
        variant="potion",
        formulas=(_formula("Breach"),),
    )

    result = WeaponPoisonAvailabilityRepository(path).catalog()

    assert result.formulas == ()
    assert any("malformed Poison payload" in row for row in result.unresolved)
