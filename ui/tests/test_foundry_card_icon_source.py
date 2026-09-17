from pathlib import Path

from ui.components import foundry_card


def test_foundry_card_heading_icons_prefer_assets_icons() -> None:
    source = Path(foundry_card.__file__).read_text(encoding="utf-8")

    direct = 'get_resource_path("assets", "icons", filename)'
    fallback = "path = icon_path(icon)"
    assert direct in source
    assert fallback in source
    assert source.index(direct) < source.index(fallback)
    assert 'self.icon_label.setPixmap(pixmap)' in source
