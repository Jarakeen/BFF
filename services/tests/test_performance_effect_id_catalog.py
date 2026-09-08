from __future__ import annotations

from services.performance_effect_id_catalog import id_to_name


def test_major_brittle_known_ids_are_available_as_debuff_fallback() -> None:
    debuffs = id_to_name(kind="debuff")

    assert debuffs[145977] == "Major Brittle"
    assert debuffs[167681] == "Major Brittle"


def test_key_support_buff_ids_are_available() -> None:
    buffs = id_to_name(kind="buff")

    assert buffs[66902] == "Major Courage"
    assert buffs[61747] == "Major Force"
    assert buffs[61744] == "Minor Berserk"
    assert buffs[93109] == "Major Slayer"


def test_key_support_debuff_ids_are_available() -> None:
    debuffs = id_to_name(kind="debuff")

    assert debuffs[61743] == "Major Breach"
    assert debuffs[61742] == "Minor Breach"
    assert debuffs[61782] == "Minor Vulnerability"
