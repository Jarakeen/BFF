from pathlib import Path

from PySide6.QtGui import QIcon


class IconService:
    """Loads SVG icons from the assets/icons folder."""

    def __init__(self) -> None:
        self.icon_folder = (
            Path(__file__).parent.parent
            / "assets"
            / "icons"
        )

    def get(self, name: str) -> QIcon:
        """Load an icon by filename (without the .svg extension)."""

        icon_path = self.icon_folder / f"{name}.svg"

        if not icon_path.exists():
            print(f"Missing icon: {icon_path}")

        return QIcon(str(icon_path))
    