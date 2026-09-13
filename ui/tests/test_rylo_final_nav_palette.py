from pathlib import Path


def test_rylo_final_navigation_override_uses_blue_not_red() -> None:
    source = Path("ui/rylo_surface_icon_fix.py").read_text(encoding="utf-8")
    block = source.split("/* Checked navigation must never fall back to Foundry teal/gold. */", 1)[1].split("/* Note/detail plates", 1)[0]
    assert "#6FA8D3" in block
    assert "#8B1E24" not in block
    assert "#281719" not in block
