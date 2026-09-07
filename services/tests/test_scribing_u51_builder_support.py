from __future__ import annotations

from pathlib import Path

from services.scribing_icons import GRIMOIRE_ICON_STEMS, texture_for_scribed_skill


def _read(relative: str) -> str:
    return (Path(__file__).resolve().parents[2] / relative).read_text(encoding='utf-8')


def test_all_u51_grimoire_icon_families_are_mapped():
    assert set(GRIMOIRE_ICON_STEMS) == {
        'Banner Bearer',
        'Elemental Explosion',
        "Mender's Bond",
        'Shield Throw',
        'Smash',
        'Soul Burst',
        'Torchbearer',
        'Trample',
        'Traveling Knife',
        "Ulfsild's Contingency",
        'Vault',
        'Wield Soul',
    }
    assert texture_for_scribed_skill('Vault', 'Poison Damage') == (
        '/esoui/art/icons/ability_grimoire_bow_poison.dds'
    )


def test_build_scribed_skill_dialog_prefers_u51_and_local_ability_icons():
    source = _read('ui/scribing_support.py')

    assert 'U51ScribingService(DEFAULT_DATABASE)' in source
    assert 'if self._u51.available' in source
    assert 'self._u51.compatible_focus(grimoire)' in source
    assert 'self._u51.result_name(grimoire, focus)' in source
    assert 'self._u51.combined_description' in source
    assert 'EsoIconResolver()' in source
    assert 'texture_for_scribed_skill(' in source
    assert '"texture": texture_for_scribed_skill(recipe.Grimoire, recipe.Focus)' in source
