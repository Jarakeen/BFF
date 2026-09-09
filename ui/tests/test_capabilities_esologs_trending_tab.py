from pathlib import Path


def test_capabilities_page_wires_esologs_trending_as_third_desk_tab():
    path = Path(__file__).resolve().parents[1] / "capabilities_page.py"
    source = path.read_text(encoding="utf-8")

    assert "from widgets.esologs_trending_card import EsoLogsTrendingCard" in source
    assert "from services.esologs_trending_service import EsoLogsTrendingService" in source
    assert 'self.desk_tabs.addTab("ESO Logs Trending")' in source
    assert "self.desk_stack.addWidget(self.trending_card)" in source
    assert "def _build_trending_service" in source
