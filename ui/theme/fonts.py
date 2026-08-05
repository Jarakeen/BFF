# ui/theme/fonts.py
from PySide6.QtGui import QFont


class Fonts:
    # ==================================================
    # Display
    # ==================================================

    @staticmethod
    def title():
        f = QFont("Cinzel", 28)
        f.setBold(True)
        return f

    @staticmethod
    def page():
        f = QFont("Cinzel", 20)
        f.setBold(True)
        return f

    @staticmethod
    def section():
        f = QFont("Cinzel", 15)
        f.setBold(True)
        return f

    @staticmethod
    def stat():
        f = QFont("Cinzel", 18)
        f.setBold(True)
        return f

    @staticmethod
    def logo():
        f = QFont("Cinzel", 22)
        f.setBold(True)
        return f


    # ==================================================
    # Atmospheric
    # ==================================================

    @staticmethod
    def subtitle():
        f = QFont("Cormorant Garamond", 14)
        f.setItalic(True)
        return f

    @staticmethod
    def note():
        f = QFont("Cormorant Garamond", 14)
        f.setItalic(True)
        return f

    @staticmethod
    def status():
        f = QFont("Cormorant Garamond", 12)
        f.setItalic(True)
        return f


    # ==================================================
    # UI / Forms
    # ==================================================

    @staticmethod
    def label():
        f = QFont("Bebas Neue", 12)
        f.setBold(True)
        return f

    @staticmethod
    def body():
        return QFont("Bebas Neue", 14)

    @staticmethod
    def button():
        f = QFont("Bebas Neue", 14)
        f.setBold(True)
        return f

    @staticmethod
    def sidebar():
        f = QFont("Bebas Neue", 14)
        f.setBold(True)
        return f

    @staticmethod
    def table():
        return QFont("Bebas Neue", 12)

    @staticmethod
    def small():
        return QFont("Bebas Neue", 10)

    @staticmethod
    def mono():
        return QFont("Cascadia Code", 10)