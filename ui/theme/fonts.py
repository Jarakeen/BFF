# ==================================================
# Black Feather Foundry
# ui/theme/fonts.py
# ==================================================

from PySide6.QtGui import QFont


class Fonts:
    """Central typography system for the Foundry UI."""

    @staticmethod
    def application_title():
        f = QFont("Cinzel", 22)
        f.setBold(True)
        return f

    @staticmethod
    def page_title():
        f = QFont("Cinzel", 17)
        f.setBold(True)
        return f

    @staticmethod
    def section_title():
        f = QFont("Cormorant Garamond", 13)
        f.setBold(True)
        return f

    @staticmethod
    def statistic():
        f = QFont("Cinzel", 16)
        f.setBold(True)
        return f

    @staticmethod
    def logo():
        f = QFont("Cinzel", 17)
        f.setBold(True)
        return f

    @staticmethod
    def subtitle():
        f = QFont("Cormorant Garamond", 12)
        f.setItalic(True)
        return f

    @staticmethod
    def note():
        f = QFont("Cormorant Garamond", 12)
        f.setItalic(True)
        return f

    @staticmethod
    def status():
        f = QFont("Cormorant Garamond", 10)
        f.setItalic(True)
        return f

    @staticmethod
    def label():
        f = QFont("Montserrat", 9)
        f.setBold(True)
        return f

    @staticmethod
    def body():
        return QFont("Montserrat", 9)

    @staticmethod
    def section():
        return Fonts.page_title()

    @staticmethod
    def button():
        f = QFont("Montserrat", 9)
        f.setBold(True)
        return f

    @staticmethod
    def sidebar():
        f = QFont("Montserrat", 9)
        f.setBold(True)
        return f

    @staticmethod
    def table():
        return QFont("Montserrat", 9)

    @staticmethod
    def small():
        return QFont("Montserrat", 8)

    @staticmethod
    def metric():
        f = QFont("Cascadia Code", 10)
        f.setBold(True)
        return f

    @staticmethod
    def mono():
        return QFont("Cascadia Code", 9)
