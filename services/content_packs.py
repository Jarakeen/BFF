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
    """Return the canonical optional collectible-icons pack directory.

    ``data_dir`` remains in the signature for compatibility with existing
    callers, but runtime no longer falls back to ``data/collectible_icons``.
    A missing content pack is a supported state: the collectibles UI remains
    usable and simply renders without optional thumbnails.
    """

    _ = data_dir
    return Path(content_packs_root) / "collectible_icons"
