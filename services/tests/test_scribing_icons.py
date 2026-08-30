from pathlib import Path

from services.eso_icon_resolver import EsoIconResolver
from services.scribing_icons import texture_for_scribed_skill


def test_warding_burst_uses_existing_soul_burst_shield_icon_texture():
    assert texture_for_scribed_skill("Soul Burst", "Damage Shield") == (
        "/esoui/art/icons/ability_grimoire_soulmagic2_shield.dds"
    )


def test_unknown_grimoire_icon_family_does_not_guess():
    assert texture_for_scribed_skill("Unknown Grimoire", "Damage Shield") == ""


def test_icon_resolver_uses_ability_icons_as_canonical_root(tmp_path: Path):
    icon_dir = tmp_path / "AbilityIcons" / "icons" / "128"
    icon_dir.mkdir(parents=True)
    expected = icon_dir / "ability_grimoire_soulmagic2_shield.png"
    expected.write_bytes(b"png")

    resolver = EsoIconResolver(tmp_path)

    assert resolver.resolve(
        "/esoui/art/icons/ability_grimoire_soulmagic2_shield.dds"
    ) == expected
