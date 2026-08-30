from __future__ import annotations

from pathlib import Path


class EsoIconResolver:
    """Resolve ESO texture references to local FoundryDock PNG assets."""

    def __init__(self, assets_root: Path | str | None = None) -> None:
        if assets_root is None:
            # services/ -> FoundryDock/
            project_root = Path(__file__).resolve().parents[1]
            assets_root = project_root / "assets"

        self.assets_root = Path(assets_root)
        self.icon_root = (
            self.assets_root
            / "AbilityIcons"
            / "icons"
            / "128"
        )

    def resolve(self, texture: str | None) -> Path | None:
        """
        Resolve an ESO texture path to a local PNG.

        Examples:
            /esoui/art/icons/ability_dragonknight_018.dds
                -> ability_dragonknight_018_a.png

            /esoui/art/icons/ability_grimoire_soulmagic2_shield.dds
                -> ability_grimoire_soulmagic2_shield.png

        Returns None when no matching local asset exists.
        """
        if not texture:
            return None

        filename = Path(texture.replace("\\", "/")).name

        if not filename:
            return None

        stem = Path(filename).stem

        candidates = [
            f"{stem}.png",
            f"{stem}_a.png",
            f"{stem}_b.png",
            f"{stem}_c.png",
        ]

        for candidate in candidates:
            path = self.icon_root / candidate
            if path.is_file():
                return path

        return None

    def exists(self, texture: str | None) -> bool:
        """Return True when a local icon can be resolved."""
        return self.resolve(texture) is not None
