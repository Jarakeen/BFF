import json

from services.paths import BROADCAST_MODULE, BROADCAST_RESOURCES


EXPECTED_STATE_FILES = {
    "CurrentBroadcast.json",
    "CurrentExpedition.json",
    "CurrentIncident.json",
    "StreamEvents.json",
    "StreamSession.json",
    "MarkerLog.md",
    "FieldNoteCounter.txt",
    "ExpeditionCounter.txt",
    "IncidentCounter.txt",
}

EXPECTED_RESOURCES = {
    "resources/natural_history_narrator.json",
    "resources/Natural_history_narrator.md",
    "resources/footnotes.txt",
}


def test_broadcast_manifest_declares_optional_payload_contract() -> None:
    manifest_path = BROADCAST_MODULE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["id"] == "broadcast"
    assert manifest["optional"] is True
    assert manifest["user_state_root"] == "user_data/broadcast"
    assert set(manifest["state_files"]) == EXPECTED_STATE_FILES
    assert set(manifest["resources"]) == EXPECTED_RESOURCES


def test_broadcast_manifest_resources_exist() -> None:
    for relative_path in EXPECTED_RESOURCES:
        path = BROADCAST_MODULE / relative_path
        assert path.is_file(), relative_path

    assert BROADCAST_RESOURCES.is_dir()
