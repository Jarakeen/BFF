# ==================================================
# Black Feather Foundry
# ui/theme/fonts.py
# ==================================================

from PySide6.QtGui import QFont


class Fonts:
    """Central typography system for the Foundry UI."""

    @staticmethod
    def _font(family: str, size: float, *, bold: bool = False, italic: bool = False):
        f = QFont(family)
        f.setPointSizeF(size)
        f.setBold(bold)
        f.setItalic(italic)
        return f

    @staticmethod
    def application_title():
        return Fonts._font("Cinzel", 22, bold=True)

    @staticmethod
    def page_title():
        return Fonts._font("Cinzel", 17, bold=True)

    @staticmethod
    def section_title():
        return Fonts._font("Cormorant Garamond", 13, bold=True)

    @staticmethod
    def statistic():
        return Fonts._font("Cinzel", 16, bold=True)

    @staticmethod
    def logo():
        return Fonts._font("Cinzel", 17, bold=True)

    @staticmethod
    def subtitle():
        return Fonts._font("Cormorant Garamond", 12, italic=True)

    @staticmethod
    def note():
        return Fonts._font("Cormorant Garamond", 12, italic=True)

    @staticmethod
    def status():
        return Fonts._font("Cormorant Garamond", 10.5, italic=True)

    @staticmethod
    def label():
        return Fonts._font("Montserrat", 9.5, bold=True)

    @staticmethod
    def body():
        return Fonts._font("Montserrat", 9.5)

    @staticmethod
    def section():
        return Fonts.page_title()

    @staticmethod
    def button():
        return Fonts._font("Montserrat", 9.5, bold=True)

    @staticmethod
    def sidebar():
        return Fonts._font("Montserrat", 9.5, bold=True)

    @staticmethod
    def table():
        return Fonts._font("Montserrat", 9.5)

    @staticmethod
    def small():
        return Fonts._font("Montserrat", 8.5)

    @staticmethod
    def metric():
        return Fonts._font("Cascadia Code", 10.5, bold=True)

    @staticmethod
    def mono():
        return Fonts._font("Cascadia Code", 9.5)
