import json
import sqlite3

import pytest

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from services.extreme_sustained_dps_generated_weapon_poison_tier_frontier_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService,
)


def _formula(*traits):
    return AlchemyFormula(
        reagents=("A", "B", "C"),
        traits=tuple(traits),
        game_update=GameUpdate.U50,
    )


def _database(tmp_path, rows):
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
        for index, (effect_name, tiers) in enumerate(rows, start=1):
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


def _tier(solvent, level, duration, triple_duration):
    return {
        "kind": "poison",
        "solvent": solvent,
        "level": level,
        "name": f"Test Poison {level}",
        "duration": duration,
        "triple_duration": triple_duration,
    }


def test_generated_poison_tier_frontier_intersects_formula_traits_by_solvent_and_level(tmp_path):
    path = _database(
        tmp_path,
        (
            (
                "Breach",
                (
                    _tier("Oil", 40, 8.0, 4.0),
                    _tier("Alkahest", 50, 10.0, 5.0),
                ),
            ),
            (
                "Protection",
                (
                    _tier("Alkahest", 50, 5.8, 2.5),
                    _tier("Different", 60, 7.0, 3.0),
                ),
            ),
        ),
    )
    formula = _formula("Breach", "Protection")

    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService(
        path
    ).frontier(formula)

    assert result.denominator_proven is True
    assert result.candidate_count == 1
    candidate = result.candidates[0]
    assert candidate.solvent == "Alkahest"
    assert candidate.level == 50
    assert candidate.item_evidence.poison_id == formula.canonical_id
    assert [
        (
            row.effect_name,
            row.base_duration_seconds,
            row.triple_duration_seconds,
            row.solvent,
            row.level,
        )
        for row in candidate.item_evidence.possible_effects
    ] == [
        ("Breach", 10.0, 5.0, "Alkahest", 50),
        ("Protection", 5.8, 2.5, "Alkahest", 50),
    ]
    assert any("No preferred poison tier" in row for row in result.evidence)


def test_generated_poison_tier_frontier_keeps_all_common_tiers_finite(tmp_path):
    path = _database(
        tmp_path,
        (
            (
                "Breach",
                (
                    _tier("Oil", 40, 8.0, 4.0),
                    _tier("Alkahest", 50, 10.0, 5.0),
                ),
            ),
            (
                "Protection",
                (
                    _tier("Oil", 40, 4.0, 2.0),
                    _tier("Alkahest", 50, 5.8, 2.5),
                ),
            ),
        ),
    )

    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService(
        path
    ).frontier(_formula("Breach", "Protection"))

    assert result.denominator_proven is True
    assert [(row.solvent, row.level) for row in result.candidates] == [
        ("Oil", 40),
        ("Alkahest", 50),
    ]


def test_generated_poison_tier_frontier_fails_closed_without_common_tier(tmp_path):
    path = _database(
        tmp_path,
        (
            ("Breach", (_tier("Oil", 40, 8.0, 4.0),)),
            ("Protection", (_tier("Alkahest", 50, 5.8, 2.5),)),
        ),
    )

    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService(
        path
    ).frontier(_formula("Breach", "Protection"))

    assert result.denominator_proven is False
    assert result.candidates == ()
    assert any("share no common solvent/level" in row for row in result.unresolved)


def test_generated_poison_tier_candidate_at_requires_proven_denominator(tmp_path):
    service = ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService(
        tmp_path / "missing.db"
    )

    with pytest.raises(ValueError, match="denominator is unresolved"):
        service.candidate_at(_formula("Breach"), 0)


def test_generated_poison_tier_frontier_fails_closed_on_malformed_wanted_trait_source(tmp_path):
    path = _database(
        tmp_path,
        (
            ("Breach", (_tier("Alkahest", 50, 10.0, 5.0),)),
            ("Protection", (_tier("Alkahest", 50, 5.8, 2.5),)),
        ),
    )
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE effect_variant SET raw_json = ? WHERE effect_id = ?",
            ("{malformed", 2),
        )

    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService(
        path
    ).frontier(_formula("Breach", "Protection"))

    assert result.denominator_proven is False
    assert any(
        "Protection has malformed imported Poison source payload" in row
        for row in result.unresolved
    )


def test_generated_poison_tier_candidate_normalizes_solvent_and_rejects_invalid_index():
    evidence = ExtremeSustainedDPSWeaponPoisonItemEvidence(
        poison_id="alchemy_formula:u50:test",
        possible_effects=(),
        source_evidence_complete=True,
    )

    candidate = ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate(
        structural_index=0,
        solvent="  Alkahest   ",
        level=50,
        item_evidence=evidence,
    )
    assert candidate.solvent == "Alkahest"

    with pytest.raises(ValueError, match="structural_index must be a non-negative integer"):
        ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate(
            structural_index=-1,
            solvent="Alkahest",
            level=50,
            item_evidence=evidence,
        )


def test_generated_poison_tier_frontier_rejects_candidate_count_drift():
    evidence = ExtremeSustainedDPSWeaponPoisonItemEvidence(
        poison_id="alchemy_formula:u50:test",
        possible_effects=(),
        source_evidence_complete=True,
    )
    candidate = ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate(
        structural_index=0,
        solvent="Alkahest",
        level=50,
        item_evidence=evidence,
    )

    with pytest.raises(ValueError, match="candidate_count must equal candidate tuple length"):
        ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontier(
            candidates=(candidate,),
            candidate_count=2,
            denominator_proven=True,
        )
