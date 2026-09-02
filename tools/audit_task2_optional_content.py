from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.paths import BROADCAST_RESOURCES, BROADCAST_USER_DATA, PROJECT_ROOT


BROADCAST_STATE_FILES = (
    "CurrentBroadcast.json",
    "CurrentExpedition.json",
    "CurrentIncident.json",
    "StreamEvents.json",
    "StreamSession.json",
    "MarkerLog.md",
    "FieldNoteCounter.txt",
    "ExpeditionCounter.txt",
    "IncidentCounter.txt",
)

BROADCAST_RESOURCE_FILES = (
    "natural_history_narrator.json",
    "Natural_history_narrator.md",
    "footnotes.txt",
    "check.png",
    "blank.png",
)

WEATHER_FILES = (
    "Clear.png",
    "Cloudy.png",
    "fog.png",
    "partly_cloudy.png",
    "rain_heavy.png",
    "rain_light.png",
    "Snow.png",
    "storm.png",
    "Wind.png",
)

LEGACY_BROADCAST_STATE = tuple(PROJECT_ROOT / "data" / name for name in BROADCAST_STATE_FILES)
LEGACY_BROADCAST_RESOURCES = (
    PROJECT_ROOT / "data" / "footnotes.txt",
    PROJECT_ROOT / "data" / "check.png",
    PROJECT_ROOT / "data" / "blank.png",
    PROJECT_ROOT / "data" / "Weather",
)


def _status(path: Path) -> str:
    return "OK" if path.exists() else "MISSING"


def main() -> int:
    content_pack = PROJECT_ROOT / "content_packs" / "collectible_icons"
    failures: list[str] = []

    print("TASK 2 OPTIONAL CONTENT CLOSEOUT AUDIT - READ ONLY")
    print()
    print("Broadcast user state:")
    for name in BROADCAST_STATE_FILES:
        path = BROADCAST_USER_DATA / name
        print(f"  {_status(path):7} {path}")
        if not path.exists():
            failures.append(str(path))

    print()
    print("Broadcast static resources:")
    for name in BROADCAST_RESOURCE_FILES:
        path = BROADCAST_RESOURCES / name
        print(f"  {_status(path):7} {path}")
        if not path.exists():
            failures.append(str(path))

    weather = BROADCAST_RESOURCES / "Weather"
    for name in WEATHER_FILES:
        path = weather / name
        print(f"  {_status(path):7} {path}")
        if not path.exists():
            failures.append(str(path))

    print()
    print("Collectible thumbnail content pack:")
    manifest = content_pack / "manifest.json"
    print(f"  {_status(manifest):7} {manifest}")
    if not manifest.exists():
        failures.append(str(manifest))
    icon_count = sum(
        1
        for path in content_pack.iterdir()
        if path.is_file() and path.name not in {"manifest.json", "manifest.pre_rebuild.json"}
    ) if content_pack.is_dir() else 0
    print(f"  icon files: {icon_count:,}")

    print()
    print("Legacy bridge still present (informational only):")
    for path in (*LEGACY_BROADCAST_STATE, *LEGACY_BROADCAST_RESOURCES):
        if path.exists():
            print(f"  PRESENT {path}")

    print()
    if failures:
        print(f"Blocking missing item count: {len(failures)}")
        return 1

    print("Blocking missing item count: 0")
    print("Task 2 canonical state/resources/content-pack layout is complete.")
    print("No files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
