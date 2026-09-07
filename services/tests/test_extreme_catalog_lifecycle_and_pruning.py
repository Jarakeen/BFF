from __future__ import annotations

import json
from itertools import product

import pytest

from services.extreme_build_catalog_runtime_service import ExtremeBuildCatalogRuntimeService
from services.extreme_build_catalog_service import (
    CATALOG_SCHEMA_VERSION,
    SUBCLASS_RULE_VERSION,
    ExtremeBuildCatalogService,
)
from services.extreme_class_route_comparison_service import ExtremeClassRouteComparisonService
from services.extreme_subclass_skill_bar_service import (
    ExtremeSubclassBarSkill,
    ExtremeSubclassSkillBarResult,
    ExtremeSubclassTwoBarResult,
)
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationResult
from services.extreme_skill_standing_effect_service import ExtremeSkillStandingEffectService


LINE_SET = ("daedric_summoning", "storm_calling", "winters_embrace")
LINE_KEY = "|".join(LINE_SET)


def _valid_row(*, flat=7440.0):
    return {
        "slot_counts": [
            ["daedric_summoning", 0],
            ["storm_calling", 0],
            ["winters_embrace", 6],
        ],
        "formulas": [
            {
                "objective_key": "physical_resistance",
                "flat": flat,
                "ratio": 0.0,
                "percent_of_reference": 0.0,
                "sources": ["Frozen Armor (6 Winter's Embrace slots)"],
            }
        ],
    }


def _payload(database, *, rows=None, schema=None, rule=None, fingerprint=None):
    service = ExtremeBuildCatalogService(database)
    return {
        "metadata": {
            "schema_version": CATALOG_SCHEMA_VERSION if schema is None else schema,
            "subclass_rule_version": SUBCLASS_RULE_VERSION if rule is None else rule,
            "source_database_sha256": (
                service.database_fingerprint() if fingerprint is None else fingerprint
            ),
        },
        "passive_allocation_formulas": {
            "by_line_set": {
                LINE_KEY: [_valid_row()] if rows is None else rows,
            }
        },
    }


def _write(database, payload):
    path = database.parent / "generated" / "extreme_build_catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_missing_catalog_cleanly_falls_back_to_live_scoring(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"db")

    runtime = ExtremeBuildCatalogRuntimeService(database)

    assert runtime.available is False
    assert runtime.reviewed_allocations(
        LINE_SET,
        "physical_resistance",
        include_known_zero=True,
    ) is None


def test_malformed_json_cleanly_falls_back_to_live_scoring(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"db")
    path = database.parent / "generated" / "extreme_build_catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ definitely not json", encoding="utf-8")

    runtime = ExtremeBuildCatalogRuntimeService(database)

    assert runtime.available is False


@pytest.mark.parametrize(
    "override",
    [
        {"schema": CATALOG_SCHEMA_VERSION + 1},
        {"rule": SUBCLASS_RULE_VERSION + "-stale"},
        {"fingerprint": "stale-fingerprint"},
    ],
)
def test_incompatible_catalog_metadata_is_rejected(tmp_path, override):
    database = tmp_path / "eso.db"
    database.write_bytes(b"db")
    _write(database, _payload(database, **override))

    runtime = ExtremeBuildCatalogRuntimeService(database)

    assert runtime.available is False


def test_database_change_invalidates_catalog_until_rebuilt(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"version-one")
    path = _write(database, _payload(database))

    first = ExtremeBuildCatalogRuntimeService(database)
    assert first.available is True

    database.write_bytes(b"version-two")
    stale = ExtremeBuildCatalogRuntimeService(database)
    assert stale.available is False

    rebuilt_payload = json.loads(path.read_text(encoding="utf-8"))
    rebuilt_payload["metadata"]["source_database_sha256"] = (
        ExtremeBuildCatalogService(database).database_fingerprint()
    )
    path.write_text(json.dumps(rebuilt_payload), encoding="utf-8")

    rebuilt = ExtremeBuildCatalogRuntimeService(database)
    assert rebuilt.available is True
    rows = rebuilt.reviewed_allocations(
        LINE_SET,
        "physical_resistance",
        include_known_zero=True,
    )
    assert rows is not None
    assert rows[0].projected_delta == pytest.approx(7440.0)


@pytest.mark.parametrize(
    "rows",
    [
        ["not-a-row"],
        [{"slot_counts": "not-a-list", "formulas": []}],
        [{"slot_counts": [["daedric_summoning", 0], ["storm_calling", 0]], "formulas": []}],
        [
            {
                "slot_counts": [
                    ["daedric_summoning", 0],
                    ["storm_calling", 0],
                    ["winters_embrace", 5],
                ],
                "formulas": [],
            }
        ],
        [
            {
                "slot_counts": [
                    ["daedric_summoning", 0],
                    ["storm_calling", 0],
                    ["wrong_line", 6],
                ],
                "formulas": [],
            }
        ],
        [
            {
                "slot_counts": [
                    ["daedric_summoning", 0],
                    ["storm_calling", 0],
                    ["winters_embrace", 6],
                ],
                "formulas": "not-a-list",
            }
        ],
        [
            {
                "slot_counts": [
                    ["daedric_summoning", 0],
                    ["storm_calling", 0],
                    ["winters_embrace", 6],
                ],
                "formulas": ["not-a-formula"],
            }
        ],
        [
            {
                "slot_counts": [
                    ["daedric_summoning", 0],
                    ["storm_calling", 0],
                    ["winters_embrace", 6],
                ],
                "formulas": [
                    {
                        "objective_key": "physical_resistance",
                        "flat": "not-a-number",
                        "ratio": 0.0,
                        "percent_of_reference": 0.0,
                        "sources": [],
                    }
                ],
            }
        ],
        [
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
                        "sources": "not-a-source-list",
                    }
                ],
            }
        ],
    ],
)
def test_malformed_cached_allocation_forces_live_fallback_instead_of_fake_empty_answer(
    tmp_path,
    rows,
):
    database = tmp_path / "eso.db"
    database.write_bytes(b"db")
    _write(database, _payload(database, rows=rows))
    runtime = ExtremeBuildCatalogRuntimeService(database)

    assert runtime.available is True
    assert runtime.reviewed_allocations(
        LINE_SET,
        "physical_resistance",
        include_known_zero=True,
    ) is None


def test_valid_empty_line_set_rows_mean_handled_but_no_candidates(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"db")
    _write(database, _payload(database, rows=[]))
    runtime = ExtremeBuildCatalogRuntimeService(database)

    assert runtime.reviewed_allocations(
        LINE_SET,
        "physical_resistance",
        include_known_zero=True,
    ) == ()


def test_unknown_line_set_returns_none_so_live_scoring_can_handle_it(tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"db")
    _write(database, _payload(database))
    runtime = ExtremeBuildCatalogRuntimeService(database)

    assert runtime.reviewed_allocations(
        ("animal_companions", "green_balance", "winters_embrace"),
        "physical_resistance",
        include_known_zero=True,
    ) is None


def _allocations_28():
    rows = []
    index = 0
    for counts in product(range(7), repeat=3):
        if sum(counts) != 6:
            continue
        rows.append(
            ExtremeSubclassSlotAllocationResult(
                objective_key="physical_resistance",
                equipped_skill_lines=LINE_SET,
                slot_counts=tuple(zip(LINE_SET, counts)),
                projected_delta=float(index),
                reviewed_sources=(f"passive-{index}",),
            )
        )
        index += 1
    assert len(rows) == 28
    return tuple(rows)


def _bar(name: str, slot_counts):
    skill = ExtremeSubclassBarSkill(
        ability_id=1 if name == "Bound Aegis" else 2,
        base_ability_id=1 if name == "Bound Aegis" else 2,
        name=name,
        skill_line_id="daedric_summoning",
        is_ultimate=False,
        morph=0,
    )
    return ExtremeSubclassSkillBarResult(slot_counts=slot_counts, skills=(skill,))


def _bare_route_service():
    return object.__new__(ExtremeClassRouteComparisonService)


def test_pruning_collapses_28_equivalent_active_and_offbar_candidates_to_one_pair(monkeypatch):
    service = _bare_route_service()
    allocations = _allocations_28()
    monkeypatch.setattr(service, "_reviewed_allocations", lambda *args, **kwargs: allocations)

    materialize_calls = []

    def materialize(front, back, **kwargs):
        materialize_calls.append((front, back))
        bar = _bar("Bound Aegis", front)
        return ExtremeSubclassTwoBarResult(front=bar, back=replace_bar_slots(bar, back))

    monkeypatch.setattr(service, "_materialize_two_bars", materialize)
    score_calls = []

    def fake_score(*args, **kwargs):
        score_calls.append((args, kwargs))
        return 0.0, (), ()

    monkeypatch.setattr(
        ExtremeSkillStandingEffectService,
        "marginal_score_build_bars_explained",
        fake_score,
    )

    result, materialized_any = service._best_reviewed_subclass_build(
        LINE_SET,
        "physical_resistance",
        reference_value=None,
        active_bar="front",
        external_effects=(),
    )

    assert materialized_any is True
    assert result is not None
    assert len(materialize_calls) == 28
    assert len(score_calls) == 1
    assert result.front_allocation.projected_delta == pytest.approx(27.0)


def replace_bar_slots(bar, slot_counts):
    return ExtremeSubclassSkillBarResult(slot_counts=slot_counts, skills=bar.skills)


def test_pruning_scores_effect_signature_product_not_raw_28_by_28_cross_product(monkeypatch):
    service = _bare_route_service()
    allocations = _allocations_28()
    monkeypatch.setattr(service, "_reviewed_allocations", lambda *args, **kwargs: allocations)

    index_by_slots = {row.slot_counts: index for index, row in enumerate(allocations)}

    def materialize(front, back, **kwargs):
        index = index_by_slots[front]
        name = "Bound Aegis" if index < 14 else "Unreviewed Filler"
        front_bar = _bar(name, front)
        back_bar = _bar(name, back)
        return ExtremeSubclassTwoBarResult(front=front_bar, back=back_bar)

    monkeypatch.setattr(service, "_materialize_two_bars", materialize)
    score_calls = []

    def fake_score(*args, **kwargs):
        score_calls.append((args, kwargs))
        return 0.0, (), ()

    monkeypatch.setattr(
        ExtremeSkillStandingEffectService,
        "marginal_score_build_bars_explained",
        fake_score,
    )

    result, _ = service._best_reviewed_subclass_build(
        LINE_SET,
        "physical_resistance",
        reference_value=None,
        active_bar="front",
        external_effects=(),
    )

    assert result is not None
    assert len(score_calls) == 4
    assert len(score_calls) < 28 * 28
