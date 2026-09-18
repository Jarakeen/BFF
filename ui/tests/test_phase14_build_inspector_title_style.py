from pathlib import Path


def test_build_inspector_identity_title_uses_compact_hero_style() -> None:
    source = Path("ui/phase14_build_inspector_support.py").read_text(encoding="utf-8")

    assert 'title.setProperty("heroTitle", True)' in source
    assert 'title.setProperty("pageTitle", True)' not in source
    assert "title.setWordWrap(True)" in source
