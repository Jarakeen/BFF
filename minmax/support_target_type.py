from enum import Enum


class SupportTargetType(str, Enum):
    """Who a support effect actually lands on."""

    SELF = "self"
    ALLY = "ally"
    GROUP = "group"
    ENEMY = "enemy"
