from pathlib import Path


def test_live_raid_surfaces_linked_map_in_hero_and_recent_activity() -> None:
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    assert 'phase_lines.append("Map Available")' in source
    assert 'f"MAP  {self._encounter_label(encounter_id)} • {linked_map.label}"' in source
    assert "def _current_linked_raid_map(self):" in source
    assert "self._render_encounter_context()" in source
    assert "self._refresh_events()" in source
