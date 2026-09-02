from pathlib import Path

from services.paths import PROJECT_ROOT


FOUNDRY = PROJECT_ROOT / "OBS Lua" / "OBS_Foundry_v1.6.lua"
FOOTNOTES = PROJECT_ROOT / "OBS Lua" / "footnotes_v1.1.lua"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_foundry_wrapper_defaults_to_split_broadcast_paths() -> None:
    text = _read(FOUNDRY)

    assert '"..\\\\user_data\\\\broadcast"' in text
    assert '"..\\\\modules\\\\broadcast\\\\resources"' in text
    assert '"broadcast_state_folder"' in text
    assert '"broadcast_resource_folder"' in text
    assert "legacy_data_folder" in text


def test_footnotes_wrapper_prefers_broadcast_module_without_moving_cover_art() -> None:
    text = _read(FOOTNOTES)

    assert '"..\\\\modules\\\\broadcast\\\\resources\\\\footnotes.txt"' in text
    assert 'dofile(script_path() .. "footnotes.lua")' in text
    assert "cover_art_file" not in text
    assert "legacy_data_folder" in text
