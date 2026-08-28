from enum import Enum


class ScalingRule(str, Enum):
    """How an ability selects the character attribute used for scaling."""

    HEALTH = "health"
    MAGICKA = "magicka"
    STAMINA = "stamina"
    HIGHEST_RESOURCE = "highest_resource"
    HIGHEST_ATTRIBUTE = "highest_attribute"
    FIXED = "fixed"
