from pathlib import Path

from services.paths import PROJECT_ROOT


OBS_FOUNDRY = PROJECT_ROOT / "OBS Lua" / "OBS_Foundry_v1.5.lua"
FOOTNOTES = PROJECT_ROOT / "OBS Lua" / "footnotes.lua"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_broadcast_obs_lua_has_no_machine_specific_user_paths() -> None:
    for path in (OBS_FOUNDRY, FOOTNOTES):
        text = _read(path).casefold()
        assert "c:\\users\\" not in text
        assert "onedrive\\desktop\\bff" not in text
        assert "onedrive\\desktop\\black feather foundry" not in text


def test_foundry_obs_exposes_portable_broadcast_folders() -> None:
    text = _read(OBS_FOUNDRY)

    assert '"broadcast_state_folder"' in text
    assert '"broadcast_resource_folder"' in text
    assert 'path_join(script_path(), "..\\\\data")' in text


def test_footnotes_defaults_are_relative_to_script_location() -> None:
    text = _read(FOOTNOTES)

    assert 'local function default_data_folder()' in text
    assert 'path_join(script_path(), "..\\\\data")' in text
    assert 'local scripts_dir = default_data_folder()' in text
