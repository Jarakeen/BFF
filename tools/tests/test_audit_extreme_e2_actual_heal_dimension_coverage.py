from __future__ import annotations

from tools.audit_extreme_e2_actual_heal_dimension_coverage import (
    E2DimensionStatus,
    build_dimension_coverage,
)


def test_e2_actual_heal_dimension_ledger_covers_every_required_roadmap_axis() -> None:
    rows = build_dimension_coverage()

    assert tuple(row.key for row in rows) == (
        "race",
        "class_route",
        "progression_passives",
        "attributes",
        "mundus",
        "food_drink",
        "potion_state",
        "armor_weights_passives",
        "gear_packages_procs",
        "traits",
        "glyphs_enchantments",
        "weapon_configuration_passives",
        "skills_morphs_ultimates",
        "champion_points",
        "class_mastery",
        "runtime_event_state",
    )
    assert all(row.owner for row in rows)
    assert all(row.evidence for row in rows)


def test_e2_actual_heal_dimension_ledger_does_not_overclaim_global_denominator() -> None:
    rows = build_dimension_coverage()
    by_key = {row.key: row for row in rows}

    assert by_key["race"].status is E2DimensionStatus.COVERED
    assert by_key["class_route"].status is E2DimensionStatus.COVERED
    assert by_key["attributes"].status is E2DimensionStatus.COVERED
    assert by_key["armor_weights_passives"].status is E2DimensionStatus.COVERED
    assert by_key["gear_packages_procs"].status is E2DimensionStatus.PARTIAL
    assert by_key["weapon_configuration_passives"].status is E2DimensionStatus.PARTIAL
    assert by_key["skills_morphs_ultimates"].status is E2DimensionStatus.PARTIAL
    assert by_key["champion_points"].status is E2DimensionStatus.PARTIAL
    assert by_key["potion_state"].status is E2DimensionStatus.CONDITIONAL
    assert by_key["class_mastery"].status is E2DimensionStatus.CONDITIONAL
    assert by_key["runtime_event_state"].status is E2DimensionStatus.CONDITIONAL
    assert any(row.status is not E2DimensionStatus.COVERED for row in rows)


def test_e2_actual_heal_dimension_ledger_keeps_open_gaps_explicit() -> None:
    rows = build_dimension_coverage()

    open_rows = tuple(row for row in rows if row.status is not E2DimensionStatus.COVERED)
    assert open_rows
    assert all(row.remaining_gap for row in open_rows)
    assert any("critical-heal evidence" in row.remaining_gap for row in open_rows)
    assert any("front/back weapon-configuration" in row.remaining_gap for row in open_rows)


def test_e2_attribute_row_records_the_full_denominator_proof() -> None:
    rows = build_dimension_coverage()
    attributes = next(row for row in rows if row.key == "attributes")

    assert attributes.status is E2DimensionStatus.COVERED
    assert "2,145" in attributes.evidence
    assert "pure Magicka/Stamina endpoints" in attributes.evidence
    assert attributes.remaining_gap == ""


def test_e2_armor_weight_row_records_physical_legality_and_reduction_proof() -> None:
    rows = build_dimension_coverage()
    armor = next(row for row in rows if row.key == "armor_weights_passives")

    assert armor.status is E2DimensionStatus.COVERED
    assert "gear_set_piece" in armor.evidence
    assert "full legal per-slot weight product" in armor.evidence
    assert "Medium-piece count" in armor.evidence
    assert "distinct armor-type count" in armor.evidence
    assert armor.remaining_gap == ""


def test_e2_gear_row_records_ordinary_denominator_without_overclaiming_special_families() -> None:
    rows = build_dimension_coverage()
    gear = next(row for row in rows if row.key == "gear_packages_procs")

    assert gear.status is E2DimensionStatus.PARTIAL
    assert "complete canonical ordinary-set corpus" in gear.evidence
    assert "authoritative five-piece candidate pool" in gear.evidence
    assert "monster/mythic/arena/proc package families" in gear.remaining_gap
