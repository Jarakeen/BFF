from __future__ import annotations

from pathlib import Path

from PIL import Image

from services.finch_raid_map_publish_service import render_raid_map_webp


def test_render_raid_map_webp_creates_small_webp(tmp_path: Path) -> None:
    source = tmp_path / "raid-map.png"
    Image.new("RGB", (960, 540), "black").save(source)

    output = render_raid_map_webp(source, tmp_path / "published.webp")

    assert output.is_file()
    assert output.suffix == ".webp"
    with Image.open(output) as rendered:
        assert rendered.format == "WEBP"
        assert rendered.size == (960, 540)
