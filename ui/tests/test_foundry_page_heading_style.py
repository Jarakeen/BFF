from pathlib import Path


def test_foundry_header_uses_collectibles_style_heading_contract() -> None:
    header = Path("ui/components/foundry_header.py").read_text(encoding="utf-8")
    fonts = Path("ui/theme/fonts.py").read_text(encoding="utf-8")
    theme = Path("ui/theme/theme_manager.py").read_text(encoding="utf-8")

    assert "class _PageHeadingLabel(QLabel):" in header
    assert 'super().setText(str(text or "").upper())' in header
    assert "self.title.setFont(Fonts.page_heading())" in header
    assert 'self.title.setProperty("foundryPageHeading", True)' in header

    assert 'Fonts._font("Montserrat", 21, bold=True)' in fonts
    assert "QFont.SpacingType.AbsoluteSpacing, 2.0" in fonts

    assert 'QLabel[pageTitle="true"] { color: #D5A85F; }' in theme
    assert 'QLabel[heroTitle="true"] { color: #E5E7E2; }' in theme
