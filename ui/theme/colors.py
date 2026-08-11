# ==========================================
# ui/theme/colors.py
# Black Feather Foundry Design System
# ==========================================

class Colors:

    BACKGROUND = "#121416"

    SURFACE = "#1B2024"

    SURFACE_LIGHT = "#232A2F"

    BORDER = "#323A41"

    BORDER_HOVER = "#56616A"

    GOLD = "#C89B5A"

    GOLD_LIGHT = "#D7B57A"

    TEXT = "#ECE8DF"

    TEXT_MUTED = "#9AA3A9"

    SUCCESS = "#6FA76D"

    WARNING = "#D5B46A"

    ERROR = "#C96A6A"

    INFO = "#5C8EC7"

    # ==================================================
    # Selection / active accent
    # ==================================================

    ACCENT = "#3E8E86"
    ACCENT_LIGHT = "#5FB0A8"

    # ==================================================
    # Parchment / field-note surfaces
    # ==================================================

    PAPER = "#2A2115"
    PAPER_LIGHT = "#352A1C"
    PAPER_BORDER = "#5A4A2E"
    PAPER_TEXT = "#E8DCC0"
    PAPER_TEXT_MUTED = "#B8A87E"

    # ==================================================
    # Severity
    # ==================================================

    SEVERITY = {
        "info": INFO,
        "success": SUCCESS,
        "warning": WARNING,
        "error": ERROR,
    }

    # ==================================================
    # Role
    # ==================================================

    ROLE = {
        "tank": "#5C8EC7",
        "healer": "#6FA76D",
        "dps": "#C96A6A",
    }

    # ==================================================
    # Status
    # ==================================================

    STATUS = {
        "online": SUCCESS,
        "offline": TEXT_MUTED,
        "warning": WARNING,
        "error": ERROR,
    }