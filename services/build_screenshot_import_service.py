from __future__ import annotations

"""Stage ESO build screenshots for a review-first import workflow.

The first version deliberately keeps capture intake separate from recognition.
ESO's Armory and Character screens expose complementary information, and the
recognition layer needs real screenshots before we can safely map pixels/text to
canonical PlayerBuild fields.  Staging the evidence now means users can capture
characters quickly without hand-entering them while that analyzer is tuned.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import uuid


_SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class BuildScreenshotIntake:
    intake_id: str
    created_at: str
    armory_image: str
    character_image: str
    status: str = "awaiting_analysis"

    def to_dict(self) -> dict:
        return asdict(self)


class BuildScreenshotImportService:
    """Owns durable screenshot evidence under ``data/build_imports``."""

    def __init__(self, root: Path):
        self.root = Path(root)

    @staticmethod
    def _validated_image(path: Path, label: str) -> Path:
        candidate = Path(path)
        if not candidate.is_file():
            raise FileNotFoundError(f"{label} screenshot does not exist: {candidate}")
        if candidate.suffix.casefold() not in _SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(_SUPPORTED_SUFFIXES))
            raise ValueError(f"{label} screenshot must be one of: {supported}")
        return candidate

    @staticmethod
    def _safe_stem(value: str) -> str:
        stem = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip()).strip("-")
        return stem[:48] or "eso-build"

    def stage(self, *, armory_image: Path, character_image: Path) -> BuildScreenshotIntake:
        armory = self._validated_image(armory_image, "Armory")
        character = self._validated_image(character_image, "Character")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        intake_id = f"{timestamp}-{uuid.uuid4().hex[:8]}"
        folder = self.root / intake_id
        folder.mkdir(parents=True, exist_ok=False)

        armory_target = folder / f"armory{armory.suffix.casefold()}"
        character_target = folder / f"character{character.suffix.casefold()}"
        shutil.copy2(armory, armory_target)
        shutil.copy2(character, character_target)

        intake = BuildScreenshotIntake(
            intake_id=intake_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            armory_image=str(armory_target),
            character_image=str(character_target),
        )

        manifest = {
            **intake.to_dict(),
            "source_files": {
                "armory": str(armory),
                "character": str(character),
            },
            "recommended_capture_pair": ["armory", "character"],
            "recognition": {
                "status": "awaiting_analysis",
                "confidence": None,
                "fields": {},
                "warnings": [
                    "Screenshot evidence is staged but has not yet been interpreted.",
                    "Imported build fields must be reviewed before saving to builds.json.",
                ],
            },
        }
        (folder / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return intake

    def pending(self) -> list[BuildScreenshotIntake]:
        if not self.root.exists():
            return []
        rows: list[BuildScreenshotIntake] = []
        for manifest_path in sorted(self.root.glob("*/manifest.json"), reverse=True):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
            if str(data.get("status", "")) != "awaiting_analysis":
                continue
            try:
                rows.append(
                    BuildScreenshotIntake(
                        intake_id=str(data["intake_id"]),
                        created_at=str(data["created_at"]),
                        armory_image=str(data["armory_image"]),
                        character_image=str(data["character_image"]),
                        status=str(data.get("status") or "awaiting_analysis"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return rows
