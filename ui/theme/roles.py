# ui/theme/roles.py

from enum import Enum, auto


class Roles:

    PRIMARY = "primary"

    SECONDARY = "secondary"

    DANGER = "danger"

    CARD = "FoundryCard"

    STAT = "statCard"

    NAV = "nav"

    PAGE_TITLE = "pageTitle"

    STATUS = "status"

class ButtonRole(Enum):
    PRIMARY = auto()
    SECONDARY = auto()
    SUCCESS = auto()
    WARNING = auto()
    DANGER = auto()
    GHOST = auto()    