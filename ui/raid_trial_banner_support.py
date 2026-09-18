from __future__ import annotations

"""Shared trial-banner artwork for Raid Plan and Live Raid surfaces."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from engine.config import get_resource_path


_TRIAL_BANNER_FILENAMES = (
    ("aetherian archive", "aetherian_archive.webp"),
    ("asylum sanctorium", "asylum_sanctorium.webp"),
    ("cloudrest", "cloudrest.webp"),
    ("dreadsail reef", "dreadsail_reef.webp"),
    ("halls of fabrication", "halls_of_fabrication.webp"),
    ("hel ra citadel", "hel_ra_citadel.webp"),
    ("kyne's aegis", "kynes_aegis.webp"),
    ("lucent citadel", "lucent_citadel.webp"),
    ("maw of lorkhaj", "maw_of_lorkhaj.webp"),
    ("ossein cage", "ossein_cage.webp"),
    ("rockgrove", "rockgrove.webp"),
    ("sanctum ophidia", "sanctum_ophidia.webp"),
    ("sanity's edge", "sanitys_edge.webp"),
    ("sunspire", "sunspire.webp"),
)

_TRIAL_BANNER_ALIASES = {
    "aa": "aetherian_archive.webp",
    "as": "asylum_sanctorium.webp",
    "cr": "cloudrest.webp",
    "dsr": "dreadsail_reef.webp",
    "hof": "halls_of_fabrication.webp",
    "hrc": "hel_ra_citadel.webp",
    "ka": "kynes_aegis.webp",
    "lc": "lucent_citadel.webp",
    "mol": "maw_of_lorkhaj.webp",
    "oc": "ossein_cage.webp",
    "rg": "rockgrove.webp",
    "so": "sanctum_ophidia.webp",
    "se": "sanitys_edge.webp",
    "ss": "sunspire.webp",
}


def _clean(value: object) -> str:
    return str(value or "").strip()


def normalize_trial_identity(value: object) -> str:
    text = _clean(value).casefold().replace("’", "'").replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def trial_banner_filename(*values: object) -> str | None:
    identities = tuple(normalize_trial_identity(value) for value in values if _clean(value))
    for identity in identities:
        if identity in _TRIAL_BANNER_ALIASES:
            return _TRIAL_BANNER_ALIASES[identity]
    identity = " ".join(identities)
    for trial_key, filename in _TRIAL_BANNER_FILENAMES:
        if trial_key in identity:
            return filename
    return None


def trial_banner_path(*values: object) -> Path | None:
    """Resolve committed or locally-added trial art without letting filenames leak into UI."""
    filename = trial_banner_filename(*values)
    banner_dir = Path(get_resource_path("assets", "raid_plans", "trial_banners"))
    if filename is not None:
        path = banner_dir / filename
        if path.is_file():
            return path

    # Local art may arrive as PNG/JPG before being converted to the normal WebP
    # release asset. Resolve by normalized stem so the page can still use it.
    identities = {
        normalize_trial_identity(value)
        for value in values
        if _clean(value)
    }
    wanted_stems = {
        identity.replace("'", "").replace(" ", "_")
        for identity in identities
    }
    if banner_dir.is_dir():
        for candidate in banner_dir.iterdir():
            if candidate.suffix.casefold() not in {".webp", ".png", ".jpg", ".jpeg"}:
                continue
            stem = normalize_trial_identity(candidate.stem).replace("'", "").replace(" ", "_")
            if stem in wanted_stems:
                return candidate
    return None


class TrialBannerLabel(QLabel):
    """Crop a wide trial image to the available hero slot without distortion."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source_pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(132)
        self.setMaximumHeight(168)
        self.setMinimumWidth(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("raidTrialBanner", True)

    def set_source(self, path: Path | None) -> None:
        self._source_pixmap = QPixmap(str(path)) if path is not None else QPixmap()
        self.setVisible(not self._source_pixmap.isNull())
        self._refresh_pixmap()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._source_pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            self.clear()
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - self.width()) // 2)
        y = max(0, (scaled.height() - self.height()) // 2)
        width = min(self.width(), scaled.width())
        height = min(self.height(), scaled.height())
        self.setPixmap(scaled.copy(x, y, width, height))


__all__ = ["TrialBannerLabel", "trial_banner_filename", "trial_banner_path"]
