from enum import Enum


class SupportTargetType(str, Enum):
    """Who a support effect actually lands on."""

    SELF = "self"
    ALLY = "ally"
    SELF_OR_ALLY = "self_or_ally"
    GROUP = "group"
    ENEMY = "enemy"
