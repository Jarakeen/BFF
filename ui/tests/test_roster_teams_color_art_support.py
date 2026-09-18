from pathlib import Path


def test_teams_uses_fixed_color_art_without_image_driven_geometry() -> None:
    source = Path("ui/raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert 'class _TeamColorArt(QLabel):' in source
    assert '"color_night_rect_1.png"' in source
    assert 'self.setFixedHeight(165)' in source
    assert 'self.setMinimumWidth(0)' in source
    assert 'QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed' in source
    assert 'Qt.AspectRatioMode.KeepAspectRatioByExpanding' in source
    assert 'self.team_sketch = _TeamColorArt()' in source
