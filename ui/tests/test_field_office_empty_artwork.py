from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from services.accessibility_preferences import VISUAL_THEME_RYLO
from ui.components.field_office_empty_artwork import FieldOfficeEmptyArtwork


def test_empty_artwork_is_theme_specific_and_real_map_replaces_it():
    app = QApplication.instance() or QApplication([])
    for filename in ("unrecorded_boss.webp", "unrecorded_mechanic.webp", "unrecorded_raid_map.webp"):
        label = FieldOfficeEmptyArtwork(filename, "No verified artwork\nField sketch only")
        label.resize(350, 220)
        assert not label._field_art.isNull()
        assert not label._rylo_art.isNull()
        old_theme = app.property("visualTheme")
        try:
            app.setProperty("visualTheme", "foundry")
            foundry = label.grab().toImage()
            app.setProperty("visualTheme", VISUAL_THEME_RYLO)
            rylo = label.grab().toImage()
            assert foundry != rylo
        finally:
            app.setProperty("visualTheme", old_theme)
        real = QPixmap(350, 220)
        real.fill(QColor("#294651"))
        label.setPixmap(real)
        assert label.pixmap().toImage().pixelColor(10, 10) == QColor("#294651")
