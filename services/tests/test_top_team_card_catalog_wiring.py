from pathlib import Path


def test_capabilities_page_wires_ranked_team_card_to_observed_template_catalog():
    source = Path("ui/capabilities_page.py").read_text(encoding="utf-8")

    assert "TopTeamTemplateIntake.for_data_dir" in source
    assert "template_intake=self.top_team_template_intake" in source
    assert "default_game_update=self.template_catalog_snapshot.game_update" in source


def test_ranked_team_card_displays_and_saves_skill_evidence():
    source = Path("widgets/top_team_card.py").read_text(encoding="utf-8")

    assert 'QLabel(f"Skills: {skills_text}")' in source
    assert '"Save Team to Catalog"' in source
    assert "include_mundus=False" in source
    assert "self._template_intake.add_team" in source


def test_capability_member_selector_uses_real_tabs_instead_of_round_buttons():
    source = Path("ui/capabilities_page.py").read_text(encoding="utf-8")

    assert "self.desk_tabs = QTabBar()" in source
    assert 'self.desk_tabs.addTab("Ranked Team Builds")' in source
    assert 'self.desk_tabs.addTab("Performance Dashboard")' in source
    assert "self.tabs_widget = QTabBar()" in source
    assert "self.tabs_widget.setUsesScrollButtons(True)" in source
    assert "FoundryTabs" not in source
