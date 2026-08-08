# ==================================================
# Black Feather Foundry
#
# File:
# ui/theme/fonts.py
#
# Purpose:
# Central typography system for the Foundry.
#
# Fonts are grouped by their purpose rather than
# by font family.
#
# ==================================================

from PySide6.QtGui import QFont


class Fonts:

    # ==================================================
    # Application Identity
    # ==================================================

    @staticmethod
    def application_title():
        """
        Main application title.
        Example:
            BLACK FEATHER FOUNDRY
        """
        f = QFont("Cinzel", 28)
        f.setBold(True)
        return f

    @staticmethod
    def page_title():
        """
        Page titles.
        Example:
            Live Operations
            Broadcast Desk
        """
        f = QFont("Cinzel", 20)
        f.setBold(True)
        return f

    @staticmethod
    def section_title():
        """
        Section / Card headings.
        """
        f = QFont("Cinzel", 15)
        f.setBold(True)
        return f

    @staticmethod
    def statistic():
        """
        Large statistics.
        Example:
            72%
            14 Pulls
        """
        f = QFont("Cinzel", 18)
        f.setBold(True)
        return f

    @staticmethod
    def logo():
        """
        Sidebar / branding.
        """
        f = QFont("Cinzel", 22)
        f.setBold(True)
        return f


    # ==================================================
    # Narrative
    # ==================================================

    @staticmethod
    def subtitle():
        """
        Atmospheric subtitles.
        """
        f = QFont("Cormorant Garamond", 14)
        f.setItalic(True)
        return f

    @staticmethod
    def note():
        """
        Journal notes.
        """
        f = QFont("Cormorant Garamond", 14)
        f.setItalic(True)
        return f

    @staticmethod
    def status():
        """
        Status bar.
        """
        f = QFont("Cormorant Garamond", 12)
        f.setItalic(True)
        return f


    # ==================================================
    # Interface
    # ==================================================

    @staticmethod
    def label():
        """
        Form labels.
        """
        f = QFont("Bebas Neue", 12)
        f.setBold(True)
        return f

    @staticmethod
    def body():
        """
        General UI text.
        """
        return QFont("Segoe UI", 10)

    @staticmethod
    def section():
        """
        Compatibility alias.
        """
        return Fonts.page_title()

    @staticmethod
    def button():
        """
        Button captions.
        """
        f = QFont("Bebas Neue", 14)
        f.setBold(True)
        return f

    @staticmethod
    def sidebar():
        """
        Sidebar navigation.
        """
        f = QFont("Bebas Neue", 14)
        f.setBold(True)
        return f

    @staticmethod
    def table():
        """
        Tables and lists.
        """
        return QFont("Segoe UI", 10)

    @staticmethod
    def small():
        """
        Small helper text.
        """
        return QFont("Segoe UI", 9)


    # ==================================================
    # Metrics
    # ==================================================

    @staticmethod
    def metric():
        """
        Timers, percentages, counters.
        """
        f = QFont("Cascadia Code", 11)
        f.setBold(True)
        return f

    @staticmethod
    def mono():
        """
        Console / logs / code.
        """
        return QFont("Cascadia Code", 10)