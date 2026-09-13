from pathlib import Path


def test_build_editor_exposes_bright_context_variant_action() -> None:
    source = Path("ui/build_context_variant_support.py").read_text(encoding="utf-8")

    assert 'FoundryCard("Context Variants")' in source
    assert 'FoundryButton("+ ADD VARIANT"' in source
    assert "background-color: #D1983D" in source
    assert 'self.context_type.addItems(["Team", "Boss", "Team + Boss"])' in source


def test_context_variant_editor_supports_full_team_build_changes() -> None:
    source = Path("ui/build_context_variant_support.py").read_text(encoding="utf-8")

    assert 'FoundryCard("Gear Overrides")' in source
    assert 'build_form.addRow("Mundus", self.mundus)' in source
    assert 'build_form.addRow("CP Override", cp_wrap)' in source
    assert 'build_form.addRow("Front Bar Overrides", self.front_bar)' in source
    assert 'context_form.addRow("Team Assignment", self.assignment)' in source
    assert "model.ContextVariants = [card.value for card in self._boss_cards]" in source
    assert "model.BossLoadouts = []" in source


def test_context_variant_support_is_installed_by_main_ui_composition() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_build_context_variant_support()" in source
    assert source.index("install_comp_builder_roster_intake_support()") < source.index(
        "install_build_context_variant_support()"
    )
