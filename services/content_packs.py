from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_app_root


CONTENT_PACKS_ROOT = get_app_root() / "content_packs"
COLLECTIBLE_ICONS_PACK = CONTENT_PACKS_ROOT / "collectible_icons"


@dataclass(frozen=True)
class ContentPackStatus:
    name: str
    root: Path
    manifest_path: Path
    installed: bool


def collectible_icons_status(
    *,
    content_packs_root: Path = CONTENT_PACKS_ROOT,
) -> ContentPackStatus:
    root = Path(content_packs_root) / "collectible_icons"
    manifest = root / "manifest.json"
    return ContentPackStatus(
        name="collectible_icons",
        root=root,
        manifest_path=manifest,
        installed=manifest.is_file(),
    )


def resolve_collectible_icons_root(
    data_dir: str | Path,
    *,
    content_packs_root: Path = CONTENT_PACKS_ROOT,
) -> Path:
    """Prefer the optional collectible-icons pack, with a legacy cache fallback.

    The legacy ``data/collectible_icons`` fallback is transitional so an
    existing local cache keeps working while users migrate it into
    ``content_packs/collectible_icons``. A missing pack is a supported state.
    """

    canonical = Path(content_packs_root) / "collectible_icons"
    if (canonical / "manifest.json").is_file():
        return canonical

    legacy = Path(data_dir) / "collectible_icons"
    if (legacy / "manifest.json").is_file():
        return legacy

    return canonical
