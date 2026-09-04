from services.accessibility_preferences import VISUAL_THEME_FOUNDRY, VISUAL_THEME_RYLO
from services.share_document_export import (
    FOUNDRY_SHARE_THEME,
    RYLO_SHARE_THEME,
    resolve_share_theme,
)


def test_foundry_share_theme_preserves_field_notes_identity():
    theme = resolve_share_theme(VISUAL_THEME_FOUNDRY)
    assert theme is FOUNDRY_SHARE_THEME
    assert theme.brand == "BLACK FEATHER FOUNDRY"
    assert theme.document_label == "FIELD NOTES"
    assert theme.accent == "#C8A46A"
    assert theme.background == "#E9D8B8"


def test_rylo_share_theme_uses_brand_board_palette_and_voice():
    theme = resolve_share_theme(VISUAL_THEME_RYLO)
    assert theme is RYLO_SHARE_THEME
    assert theme.brand == "RYLO"
    assert theme.document_label == "OPERATIONS RECORD"
    assert theme.motto == "CROSS THE DARKNESS."
    assert theme.background == "#0B0B0E"
    assert theme.surface == "#1A1A1E"
    assert theme.rule == "#2B2B31"
    assert theme.text == "#BEB6A6"
    assert theme.accent == "#8B0E14"
    assert theme.alert == "#C79A3B"


def test_unknown_theme_falls_back_to_foundry():
    assert resolve_share_theme("mystery-theme") is FOUNDRY_SHARE_THEME
