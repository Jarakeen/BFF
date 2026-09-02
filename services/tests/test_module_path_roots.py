from services.paths import (
    BROADCAST_MODULE,
    BROADCAST_RESOURCES,
    BROADCAST_USER_DATA,
    MODULES,
    NARRATOR,
    PROJECT_ROOT,
    USER_DATA,
)


def test_module_and_user_data_roots_are_canonical() -> None:
    assert MODULES == PROJECT_ROOT / "modules"
    assert USER_DATA == PROJECT_ROOT / "user_data"
    assert BROADCAST_MODULE == MODULES / "broadcast"
    assert BROADCAST_RESOURCES == BROADCAST_MODULE / "resources"
    assert BROADCAST_USER_DATA == USER_DATA / "broadcast"


def test_broadcast_narrator_lives_in_module_resources() -> None:
    assert NARRATOR == BROADCAST_RESOURCES / "natural_history_narrator.json"
    assert NARRATOR.exists()
    assert (BROADCAST_RESOURCES / "Natural_history_narrator.md").exists()
    assert (BROADCAST_RESOURCES / "footnotes.txt").exists()
