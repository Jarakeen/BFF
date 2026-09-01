from __future__ import annotations

import ast
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BROADCAST_PAGES = {
    "ui/broadcast_page.py",
    "ui/field_notes_page.py",
    "ui/stream_elements_page.py",
    "ui/archive_page.py",
}

BROADCAST_WIDGET_PREFIXES = (
    "widgets/broadcast_",
    "widgets/field_notes_",
    "widgets/session_panel.py",
    "widgets/raid_controls.py",
    "widgets/timeline_panel.py",
    "widgets/narrator_panel.py",
    "widgets/stream_controls.py",
    "widgets/archive_",
)

BROADCAST_SERVICE_FILES = {
    "services/broadcast_generator.py",
    "services/narrator_service.py",
    "services/obs_websocket_service.py",
    "services/stream_event_service.py",
}

SHARED_SERVICE_FILES = {
    "services/archive_service.py",
    "services/archive_record.py",
    "services/expedition_service.py",
    "services/raid_service.py",
    "services/roster_service.py",
    "services/settings_service.py",
    "services/eso_database.py",
}

BROADCAST_DATA_NAMES = {
    "CurrentBroadcast.json",
    "StreamEvents.json",
    "StreamSession.json",
    "FieldNoteCounter.txt",
    "MarkerLog.md",
    "TamrielDate.txt",
    "footnotes.txt",
    "natural_history_narrator.json",
    "check.png",
    "blank.png",
}

BROADCAST_SETTINGS = {
    "CurrentBroadcastPath",
    "StreamEventsPath",
    "StreamSessionPath",
    "BossLogPath",
    "NarratorContentPath",
    "BrbSceneName",
    "EndOfStreamSceneName",
    "ObsWebSocketHost",
    "ObsWebSocketPort",
    "ObsWebSocketPassword",
    "WeatherFolder",
    "MarkerLogPath",
}

CORE_COUPLING_FILES = {
    "ui/main_window.py",
    "ui/components/foundry_sidebar.py",
    "ui/settings_page.py",
    "services/settings_service.py",
    "packaging/build_friend.ps1",
    "packaging/BFF.spec",
}

ABSOLUTE_WINDOWS_PATH = re.compile(r"[A-Za-z]:\\\\Users\\\\")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def existing(paths: set[str]) -> list[str]:
    return sorted(path for path in paths if (ROOT / path).exists())


def widget_files() -> list[str]:
    base = ROOT / "widgets"
    if not base.exists():
        return []
    results = []
    for path in base.glob("*.py"):
        value = rel(path)
        if any(value == prefix or value.startswith(prefix) for prefix in BROADCAST_WIDGET_PREFIXES):
            results.append(value)
    return sorted(results)


def data_files() -> list[str]:
    data = ROOT / "data"
    if not data.exists():
        return []
    return sorted(rel(path) for path in data.rglob("*") if path.is_file() and path.name in BROADCAST_DATA_NAMES)


def obs_files() -> list[str]:
    folder = ROOT / "OBS Lua"
    if not folder.exists():
        return []
    return sorted(rel(path) for path in folder.glob("*.lua"))


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def core_couplings() -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    needles = (
        "BroadcastPage",
        "FieldNotesPage",
        "LiveOperationsPage",
        "ArchivePage",
        '"broadcast"',
        "ObsWebSocketService",
    ) + tuple(BROADCAST_SETTINGS)
    for filename in sorted(CORE_COUPLING_FILES):
        path = ROOT / filename
        if not path.exists():
            continue
        body = text(path)
        found = sorted({needle for needle in needles if needle in body})
        if found:
            hits.append((filename, ", ".join(found)))
    return hits


def shared_service_consumers() -> dict[str, list[str]]:
    module_names = {Path(name).stem for name in SHARED_SERVICE_FILES}
    consumers: dict[str, list[str]] = {name: [] for name in sorted(module_names)}
    for root, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__", "build", "dist", "old_pages"}]
        for name in names:
            if not name.endswith(".py"):
                continue
            path = Path(root) / name
            relative = rel(path)
            if relative in SHARED_SERVICE_FILES:
                continue
            try:
                tree = ast.parse(text(path))
            except SyntaxError:
                continue
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("services."):
                    imported.add(node.module.split(".")[-1])
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("services."):
                            imported.add(alias.name.split(".")[-1])
            for module in imported & module_names:
                consumers[module].append(relative)
    return {key: sorted(value) for key, value in consumers.items() if value}


def hardcoded_obs_paths() -> list[str]:
    hits = []
    for filename in obs_files():
        if ABSOLUTE_WINDOWS_PATH.search(text(ROOT / filename)):
            hits.append(filename)
    return hits


def narrator_mismatches() -> list[str]:
    candidates = {
        "services.paths.NARRATOR": ROOT / "data" / "Natural_history_narrator.md",
        "root Natural_history_narrator.md": ROOT / "Natural_history_narrator.md",
        "data natural_history_narrator.json": ROOT / "data" / "natural_history_narrator.json",
        "LiveOperations legacy nat_his_nar.md": ROOT / "nat_his_nar.md",
    }
    return [f"{label}: exists={path.exists()} path={rel(path)}" for label, path in candidates.items()]


def main() -> int:
    print("=" * 78)
    print(" BROADCAST MODULE BOUNDARY AUDIT - READ ONLY")
    print("=" * 78)
    print(f"repo: {ROOT}")
    print()

    print("=== CANDIDATE MODULE UI ===")
    for item in existing(BROADCAST_PAGES) + widget_files():
        print(f"  {item}")
    print()

    print("=== CANDIDATE MODULE SERVICES ===")
    for item in existing(BROADCAST_SERVICE_FILES):
        print(f"  {item}")
    print()

    print("=== SHARED SERVICES - KEEP IN CORE ===")
    for item in existing(SHARED_SERVICE_FILES):
        print(f"  {item}")
    print()

    print("=== BROADCAST / OBS DATA CANDIDATES ===")
    for item in data_files():
        print(f"  {item}")
    print()

    print("=== OBS LUA ===")
    hardcoded = hardcoded_obs_paths()
    for item in obs_files():
        marker = " [ABSOLUTE PATHS]" if item in hardcoded else ""
        print(f"  {item}{marker}")
    print()

    print("=== CORE COUPLINGS TO REMOVE OR GATE ===")
    couplings = core_couplings()
    if not couplings:
        print("  (none)")
    else:
        for filename, detail in couplings:
            print(f"  {filename}: {detail}")
    print()

    print("=== SHARED-SERVICE CONSUMERS ===")
    for module, consumers in shared_service_consumers().items():
        print(f"  {module}:")
        for consumer in consumers:
            print(f"    - {consumer}")
    print()

    print("=== NARRATOR PATH CONSISTENCY ===")
    for item in narrator_mismatches():
        print(f"  {item}")
    print()

    print(f"core coupling files: {len(couplings)}")
    print(f"OBS scripts with absolute Windows paths: {len(hardcoded)}")
    print("No files, settings, archives, OBS state, or databases were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
