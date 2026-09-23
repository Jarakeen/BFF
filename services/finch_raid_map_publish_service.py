from __future__ import annotations

"""Publish small, flattened Raid Map previews to Finch for raid-night clients.

FoundryDock keeps the editable Raid Map state locally. Finch receives only a
WebP snapshot plus the minimum encounter metadata needed by mobile/web clients.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from PIL import Image

from services.finch_api_client import FinchApiClient
from services.settings_service import SettingsService


_MAX_WEBP_WIDTH = 1280
_WEBP_QUALITY = 74


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _slug(value: object) -> str:
    text = _clean(value).casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "map"


@dataclass(frozen=True, slots=True)
class FinchRaidMapPreview:
    encounter_id: str
    encounter_name: str
    map_label: str
    map_image_url: str
    note: str = ""
    content_sha256: str = ""


def render_raid_map_webp(
    source: Path,
    destination: Path,
    *,
    max_width: int = _MAX_WEBP_WIDTH,
    quality: int = _WEBP_QUALITY,
) -> Path:
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise FileNotFoundError(source)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.load()
        rendered = image.convert("RGB")
        width = max(1, int(max_width))
        if rendered.width > width:
            height = max(1, round(rendered.height * width / rendered.width))
            rendered = rendered.resize((width, height), Image.Resampling.LANCZOS)
        rendered.save(
            destination,
            format="WEBP",
            quality=max(1, min(100, int(quality))),
            method=6,
        )
    return destination


def publish_raid_map_webp_to_finch(
    *,
    source: Path,
    plan_id: str,
    encounter_id: str,
    encounter_name: str,
    map_label: str,
    note: str = "",
    data_dir: Path,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> FinchRaidMapPreview:
    plan_key = _clean(plan_id)
    encounter_key = _clean(encounter_id)
    if not plan_key:
        raise ValueError("A saved Raid Plan is required before publishing a Raid Map.")
    if not encounter_key:
        raise ValueError("An encounter is required before publishing a Raid Map.")

    source = Path(source)
    published_dir = Path(data_dir) / "raid_maps" / "published"
    base_name = f"{_slug(plan_key)}__{_slug(encounter_key)}"
    webp_path = published_dir / f"{base_name}.webp"
    render_raid_map_webp(source, webp_path)

    content = webp_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    asset_key = f"raid-map__{base_name}__{digest[:16]}.webp"

    settings = SettingsService(Path(settings_path)).load()
    client = FinchApiClient(
        base_url=str(settings.get("FinchApiUrl") or ""),
        api_key=str(settings.get("FinchApiKey") or ""),
        timeout=timeout,
    )
    public_url = client.publish_shared_asset(
        asset_key=asset_key,
        content=content,
        content_type="image/webp",
    )
    return FinchRaidMapPreview(
        encounter_id=encounter_key,
        encounter_name=_clean(encounter_name) or encounter_key,
        map_label=_clean(map_label) or "Raid Map",
        map_image_url=public_url,
        note=_clean(note),
        content_sha256=digest,
    )


def publish_raid_map_and_plan_to_finch(
    *,
    source: Path,
    plan_id: str,
    encounter_id: str,
    encounter_name: str,
    map_label: str,
    note: str = "",
    data_dir: Path,
    settings_path: Path = Path("settings.json"),
    timeout: float = 10.0,
) -> FinchRaidMapPreview:
    preview = publish_raid_map_webp_to_finch(
        source=source,
        plan_id=plan_id,
        encounter_id=encounter_id,
        encounter_name=encounter_name,
        map_label=map_label,
        note=note,
        data_dir=data_dir,
        settings_path=settings_path,
        timeout=timeout,
    )

    from services.raid_section_state_service import RaidSectionStateService
    from services.finch_shared_publish_service import publish_raid_plan_to_finch

    RaidSectionStateService().set_finch_raid_map_preview(
        plan_id,
        encounter_id,
        {
            "encounter_id": preview.encounter_id,
            "encounter_name": preview.encounter_name,
            "map_label": preview.map_label,
            "map_image_url": preview.map_image_url,
            "note": preview.note,
            "content_sha256": preview.content_sha256,
        },
    )
    publish_raid_plan_to_finch(
        database_path=Path(data_dir) / "eso.db",
        raid_plans_path=Path(data_dir) / "raid_plans.json",
        plan_id=plan_id,
        settings_path=settings_path,
        timeout=timeout,
    )
    return preview


__all__ = [
    "FinchRaidMapPreview",
    "publish_raid_map_webp_to_finch",
    "publish_raid_map_and_plan_to_finch",
    "render_raid_map_webp",
]
