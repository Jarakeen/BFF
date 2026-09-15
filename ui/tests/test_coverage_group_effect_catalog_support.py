from pathlib import Path


def test_coverage_group_effect_support_removes_utility_filter_and_keeps_magickasteal_as_debuff():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert 'coverage_page.UTILITY = set()' in source
    assert 'self.effect_filter.findText("Utility")' in source
    assert 'coverage_page.DEBUFFS = set(DEBUFF_NAMES)' in source


def test_coverage_group_effect_support_puts_sources_in_coverage_notes():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert '"Coverage Notes"' in source
    assert '"Known group-capable sources:' in source
    assert 'reference.source_notes' in source
    assert 'These are planning references.' not in source


def test_coverage_group_effect_support_does_not_promote_unmapped_reference_effects():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert 'status = {name: "unverified" for name in COVERAGE_NAMES}' in source
    assert 'if name in snapshot.status:' in source


def test_unique_support_sets_extend_coverage_without_duplicate_rows():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert 'UNIQUE_SUPPORT_SET_NAMES' in source
    assert 'tuple(dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES)))' in source
    assert 'REFERENCE_BY_NAME = {**GROUP_COVERAGE_BY_NAME, **UNIQUE_SUPPORT_SET_BY_NAME}' in source


def test_unique_support_sets_get_short_type_labels_in_coverage_table():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert 'getattr(reference, "type_label", "") or reference.category' in source
    assert 'Unique support-set effect; see Coverage Notes for source details.' in source


def test_unique_support_sets_have_their_own_filter():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert 'self.effect_filter.addItem("Unique Buffs")' in source
    assert 'category = "Unique Buffs"' in source
    assert 'CoveragePage._apply_coverage_filters = _apply_coverage_filters_with_unique' in source


def test_named_canonical_effects_are_projected_before_unique_set_overlay():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert "RaidNamedGroupEffectCapabilityService" in source
    assert "capability_service = getattr(self, \"capability_service\", None)" in source
    assert "capability_service=capability_service" in source
    assert "RaidUniqueSupportSetCapabilityService().overlay(snapshot, selected_builds)" in source
