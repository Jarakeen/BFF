from pathlib import Path


def test_support_gear_widget_splits_healer_and_tank_sections() -> None:
    source = Path("widgets/support_gear_reference.py").read_text(encoding="utf-8")

    assert '"Healer Support Sets"' in source
    assert '"Tank Support Sets"' in source
    assert 'QPushButton("+ Add Set")' in source
    assert 'table.setHorizontalHeaderLabels(("Set", "Covers", "Notes"))' in source
    assert "SupportGearReferenceService" in source


def test_support_gear_add_dialog_uses_role_specific_entry_and_catalog_autocomplete() -> None:
    source = Path("widgets/support_gear_reference.py").read_text(encoding="utf-8")

    assert "set_name_choices=self.set_name_choices" in source
    assert "GearSetRepository(DEFAULT_DATABASE).list_sets()" in source
    assert "QCompleter(set_name_choices, self)" in source
    assert "role=self.role" in source


def test_top_gear_places_support_gear_third() -> None:
    source = Path("ui/capabilities_page.py").read_text(encoding="utf-8")

    ranked = source.index('self.desk_tabs.addTab("Ranked Team Builds")')
    trending = source.index('self.desk_tabs.addTab("ESO Logs Trending")')
    support = source.index('self.desk_tabs.addTab("Support Gear")')
    performance = source.index('self.desk_tabs.addTab("Performance Dashboard")')

    assert ranked < trending < support < performance
    assert "self.support_gear_reference = SupportGearReferenceWidget()" in source
