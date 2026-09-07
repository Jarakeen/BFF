from __future__ import annotations

import json
from types import SimpleNamespace

from minmax.character_build.character_class import CharacterClass
from services.extreme_build_catalog_runtime_service import ExtremeBuildCatalogRuntimeService
from services.extreme_build_catalog_service import (
    CATALOG_SCHEMA_VERSION,
    SUBCLASS_RULE_VERSION,
    ExtremeBuildCatalogService,
)
from services.extreme_class_route_comparison_service import ExtremeClassRouteComparisonService


def _write_catalog(database, *, fingerprint: str, formulas):
    path = database.parent / "generated" / "extreme_build_catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "schema_version": CATALOG_SCHEMA_VERSION,
                    "subclass_rule_version": SUBCLASS_RULE_VERSION,
                    "source_database_sha256": fingerprint,
                },
                "passive_allocation_formulas": {
                    "by_line_set": {
                        "daedric_summoning|storm_calling|winters_embrace": formulas,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_runtime_catalog_rehydrates_flat_passive_formula(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"runtime-catalog")
    fingerprint = ExtremeBuildCatalogService(database).database_fingerprint()
    _write_catalog(
        database,
        fingerprint=fingerprint,
        formulas=[
            {
                "slot_counts": [
                    ["daedric_summoning", 0],
                    ["storm_calling", 0],
                    ["winters_embrace", 6],
                ],
                "formulas": [
                    {
                        "objective_key": "physical_resistance",
                        "flat": 7440.0,
                        "ratio": 0.0,
                        "percent_of_reference": 0.0,
                        "sources": ["Frozen Armor (6 Winter's Embrace slots)"],
                    }
                ],
            }
        ],
    )

    runtime = ExtremeBuildCatalogRuntimeService(database)
    rows = runtime.reviewed_allocations(
        ("daedric_summoning", "storm_calling", "winters_embrace"),
        "physical_resistance",
        include_known_zero=True,
    )

    assert runtime.available is True
    assert rows is not None
    assert len(rows) == 1
    assert rows[0].projected_delta == 7440.0
    assert rows[0].reviewed_sources == ("Frozen Armor (6 Winter's Embrace slots)",)


def test_runtime_catalog_keeps_reference_dependent_formula_unresolved_without_reference(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"runtime-percent")
    fingerprint = ExtremeBuildCatalogService(database).database_fingerprint()
    _write_catalog(
        database,
        fingerprint=fingerprint,
        formulas=[
            {
                "slot_counts": [
                    ["daedric_summoning", 0],
                    ["storm_calling", 0],
                    ["winters_embrace", 6],
                ],
                "formulas": [
                    {
                        "objective_key": "magicka_recovery",
                        "flat": 0.0,
                        "ratio": 0.0,
                        "percent_of_reference": 0.20,
                        "sources": ["Synthetic reviewed percent"],
                    }
                ],
            }
        ],
    )

    runtime = ExtremeBuildCatalogRuntimeService(database)
    unresolved = runtime.reviewed_allocations(
        ("daedric_summoning", "storm_calling", "winters_embrace"),
        "magicka_recovery",
        reference_value=None,
        include_known_zero=True,
    )
    resolved = runtime.reviewed_allocations(
        ("daedric_summoning", "storm_calling", "winters_embrace"),
        "magicka_recovery",
        reference_value=1000.0,
        include_known_zero=True,
    )

    assert unresolved == ()
    assert resolved is not None
    assert resolved[0].projected_delta == 200.0


def test_runtime_catalog_rejects_stale_database_fingerprint(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"current-database")
    _write_catalog(database, fingerprint="stale", formulas=[])

    runtime = ExtremeBuildCatalogRuntimeService(database)

    assert runtime.available is False
    assert runtime.reviewed_allocations(
        ("daedric_summoning", "storm_calling", "winters_embrace"),
        "physical_resistance",
        include_known_zero=True,
    ) is None


def test_compare_solves_duplicate_line_set_once_per_context(tmp_path, monkeypatch):
    database = tmp_path / "eso.db"
    database.write_bytes(b"")
    service = ExtremeClassRouteComparisonService(database)
    monkeypatch.setattr(service.mastery_pairs, "best_pure_class_routes", lambda *args, **kwargs: ())

    line_set = ("aedric_spear", "green_balance", "herald_of_the_tome")
    configs = [
        SimpleNamespace(
            is_pure_class=False,
            base_class=CharacterClass.ARCANIST,
            equipped_skill_lines=line_set,
        ),
        SimpleNamespace(
            is_pure_class=False,
            base_class=CharacterClass.TEMPLAR,
            equipped_skill_lines=line_set,
        ),
    ]
    monkeypatch.setattr(
        "services.extreme_class_route_comparison_service.ExtremeClassConfigurationService.all_candidates",
        lambda: configs,
    )

    calls = []

    def fake_best(*args, **kwargs):
        calls.append(args[0])
        return None, True

    monkeypatch.setattr(service, "_best_reviewed_subclass_build", fake_best)

    result = service.compare("spell_damage", reference_value=5000.0)

    assert len(calls) == 1
    assert calls == [line_set]
    assert len(result.routes) == 2
