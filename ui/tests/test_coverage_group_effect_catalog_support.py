from pathlib import Path


def test_coverage_group_effect_support_removes_utility_filter_and_keeps_magickasteal_as_debuff():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert 'coverage_page.UTILITY = set()' in source
    assert 'self.effect_filter.findText("Utility")' in source
    assert 'coverage_page.DEBUFFS = set(GROUP_DEBUFF_NAMES)' in source


def test_coverage_group_effect_support_puts_sources_in_coverage_notes():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert '"Coverage Notes"' in source
    assert '"Known group-capable sources:' in source
    assert 'reference.source_notes' in source


def test_coverage_group_effect_support_does_not_promote_unmapped_reference_effects():
    source = Path("ui/coverage_group_effect_catalog_support.py").read_text(encoding="utf-8")
    assert 'status = {name: "unverified" for name in GROUP_COVERAGE_NAMES}' in source
    assert 'if name in snapshot.status:' in source
