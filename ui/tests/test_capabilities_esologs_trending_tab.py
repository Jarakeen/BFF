from pathlib import Path


def test_capabilities_page_wires_esologs_trending_as_second_desk_tab():
    path = Path(__file__).resolve().parents[1] / "capabilities_page.py"
    source = path.read_text(encoding="utf-8")

    assert "from widgets.esologs_trending_card import EsoLogsTrendingCard" in source
    assert "from services.esologs_trending_service import EsoLogsTrendingService" in source
    assert "def _build_trending_service" in source

    ranked = source.index('self.desk_tabs.addTab("Ranked Team Builds")')
    trending = source.index('self.desk_tabs.addTab("ESO Logs Trending")')
    performance = source.index('self.desk_tabs.addTab("Performance Dashboard")')
    assert ranked < trending < performance

    ranked_stack = source.index("self.desk_stack.addWidget(self.top_team_card)")
    trending_stack = source.index("self.desk_stack.addWidget(self.trending_card)")
    performance_stack = source.index(
        "self.desk_stack.addWidget(self.performance_member_column)"
    )
    assert ranked_stack < trending_stack < performance_stack
