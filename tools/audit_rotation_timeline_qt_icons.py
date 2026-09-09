from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from engine.config import get_data_dir
from services.build_service import BuildService
from services.rotation_timeline_projection_service import RotationTimelineProjectionService
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport
from ui.rotation_timeline_dashboard_support import RotationTimelineIconResolver


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or "Unnamed Character"
    ).strip()


def _build_name(build) -> str:
    return str(getattr(build, "BuildName", "") or "Current Build").strip()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    _ = app

    roster = BuildService(get_data_dir() / "builds.json").load()
    build = next(
        (
            member
            for member in roster.Members
            if _character_name(member).casefold() == "magrat"
            and _build_name(member).casefold() == "df healer"
        ),
        None,
    )
    if build is None:
        print("Magrat -> DF Healer not found")
        return 1

    generated = RotationGenerationSupport().generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=60.0,
            rotation_type="Semi-static",
        ),
    )
    resolver = RotationTimelineIconResolver()
    projection = RotationTimelineProjectionService().project(
        generated.plan,
        duration_evidence=generated.duration_evidence,
        icon_path_resolver=resolver.resolve,
    )

    print("ROTATION TIMELINE QT ICON AUDIT")
    print("=" * 88)
    print(f"Plan actions:      {len(generated.plan.actions)}")
    print(f"Projected icons:   {len(projection.actions)}")
    print()

    failures = 0
    seen: set[tuple[str, str | None]] = set()
    for action in projection.actions:
        identity = (action.name, action.icon_path)
        if identity in seen:
            continue
        seen.add(identity)

        path = Path(action.icon_path) if action.icon_path else None
        exists = bool(path is not None and path.is_file())
        icon = QIcon(str(path)) if path is not None else QIcon()
        pixmap = icon.pixmap(QSize(38, 38))
        icon_null = icon.isNull()
        pixmap_null = pixmap.isNull()

        print(f"{action.name}")
        print(f"  icon_key:     {action.icon_key}")
        print(f"  icon_path:    {action.icon_path or 'NONE'}")
        print(f"  file_exists:  {exists}")
        print(f"  QIcon null:   {icon_null}")
        print(f"  pixmap null:  {pixmap_null}")
        print(f"  pixmap size:  {pixmap.width()}x{pixmap.height()}")
        print()

        if not exists or icon_null or pixmap_null:
            failures += 1

    print("=" * 88)
    print(f"Unique projected icon failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
