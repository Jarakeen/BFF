from services.minmax.build import Build
from services.minmax.build_glyph import BuildArmorGlyph


HEALTH_GLYPH_ID = 26580
PRISMATIC_GLYPH_ID = 68343


def test_build_starts_with_no_armor_glyphs():
    build = Build()

    assert build.armor_glyphs == []


def test_build_can_add_armor_glyph():
    build = Build()

    build.add_armor_glyph(HEALTH_GLYPH_ID)

    assert build.armor_glyphs == [
        BuildArmorGlyph(
            item_id=HEALTH_GLYPH_ID,
        )
    ]


def test_build_can_contain_multiple_armor_glyphs():
    build = Build()

    build.add_armor_glyph(HEALTH_GLYPH_ID)
    build.add_armor_glyph(PRISMATIC_GLYPH_ID)

    assert build.armor_glyphs == [
        BuildArmorGlyph(item_id=HEALTH_GLYPH_ID),
        BuildArmorGlyph(item_id=PRISMATIC_GLYPH_ID),
    ]


def test_armor_glyph_is_immutable():
    glyph = BuildArmorGlyph(
        item_id=HEALTH_GLYPH_ID,
    )

    try:
        glyph.item_id = PRISMATIC_GLYPH_ID
    except Exception:
        pass
    else:
        raise AssertionError("BuildArmorGlyph should be immutable")