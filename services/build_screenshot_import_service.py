from __future__ import annotations

"""Stage ESO build screenshots for a review-first import workflow.

ESO's Armory spreads useful build evidence across several subviews (equipment,
skills, Champion Points, attributes).  A complete import therefore needs to keep
multiple Armory captures together with one matching Character-sheet capture.
This service stores that evidence without interpreting or writing build state yet.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import uuid
from collections.abc import Iterable


_SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class BuildScreenshotIntake:
    intake_id: str
    created_at: str
    armory_image: str
    character_image: str
    status: str = "awaiting_analysis"
    armory_images: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["armory_images"] = list(self.armory_images)
        return payload


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

    @staticmethod
    def _normalize_armory_inputs(
        armory_image: Path | None,
        armory_images: Iterable[Path] | None,
    ) -> list[Path]:
        rows: list[Path] = []
        if armory_image is not None:
            rows.append(Path(armory_image))
        if armory_images is not None:
            rows.extend(Path(value) for value in armory_images)

        unique: list[Path] = []
        seen: set[str] = set()
        for row in rows:
            key = str(row.resolve()) if row.exists() else str(row)
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique

    def stage(
        self,
        *,
        character_image: Path,
        armory_image: Path | None = None,
        armory_images: Iterable[Path] | None = None,
    ) -> BuildScreenshotIntake:
        armory_sources = self._normalize_armory_inputs(armory_image, armory_images)
        if not armory_sources:
            raise ValueError("Choose at least one Armory screenshot.")

        armory_sources = [
            self._validated_image(path, "Armory") for path in armory_sources
        ]
        character = self._validated_image(character_image, "Character")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        intake_id = f"{timestamp}-{uuid.uuid4().hex[:8]}"
        folder = self.root / intake_id
        folder.mkdir(parents=True, exist_ok=False)

        armory_targets: list[Path] = []
        for index, armory in enumerate(armory_sources, start=1):
            # Keep the historical one-screen filename for compatibility, while
            # multi-screen imports get deterministic numbered evidence files.
            filename = (
                f"armory{armory.suffix.casefold()}"
                if len(armory_sources) == 1
                else f"armory-{index:02d}{armory.suffix.casefold()}"
            )
            target = folder / filename
            shutil.copy2(armory, target)
            armory_targets.append(target)

        character_target = folder / f"character{character.suffix.casefold()}"
        shutil.copy2(character, character_target)

        intake = BuildScreenshotIntake(
            intake_id=intake_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            armory_image=str(armory_targets[0]),
            armory_images=tuple(str(path) for path in armory_targets),
            character_image=str(character_target),
        )

        manifest = {
            **intake.to_dict(),
            "source_files": {
                "armory": [str(path) for path in armory_sources],
                "character": str(character),
            },
            "recommended_capture_set": [
                "armory_equipment",
                "armory_skills",
                "armory_champion",
                "character_sheet",
            ],
            # Retained for older tooling that only knew about a pair.
            "recommended_capture_pair": ["armory", "character"],
            "recognition": {
                "status": "awaiting_analysis",
                "confidence": None,
                "fields": {},
                "warnings": [
                    "Screenshot evidence is staged but has not yet been interpreted.",
                    "Imported build fields must be reviewed before saving to builds.json.",
                    "Armory data may span several subviews; all supplied Armory screenshots belong to this one build intake.",
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
                armory_images = tuple(
                    str(value)
                    for value in (data.get("armory_images") or [])
                    if str(value).strip()
                )
                primary = str(data.get("armory_image") or "")
                if not armory_images and primary:
                    armory_images = (primary,)
                rows.append(
                    BuildScreenshotIntake(
                        intake_id=str(data["intake_id"]),
                        created_at=str(data["created_at"]),
                        armory_image=primary or (armory_images[0] if armory_images else ""),
                        armory_images=armory_images,
                        character_image=str(data["character_image"]),
                        status=str(data.get("status") or "awaiting_analysis"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return rows
