from pathlib import Path


def test_trending_replaces_player_loadouts_with_momentum_sections_and_clickable_sets():
    path = Path(__file__).resolve().parents[2] / "widgets" / "esologs_trending_card.py"
    source = path.read_text(encoding="utf-8")

    assert 'QLabel("Top Player Loadouts")' not in source
    assert '"Making Waves"' in source
    assert '"Cooling Off"' in source
    assert '"New Arrival"' in source
    assert '"Breakout"' in source
    assert '"*Just for fun:' in source

    assert "linkActivated.connect(self._emit_set_link)" in source
    assert 'pages.get("gear_lookup")' in source
    assert 'show_page("gear_lookup")' in source
    assert "search.setText(set_name)" in source
    assert "setCurrentItem(item)" in source
