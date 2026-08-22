from enum import Enum


class SupportEffectCategory(str, Enum):
    """The buff/debuff/status distinction requested for group support effects."""

    BUFF = "buff"
    DEBUFF = "debuff"
    STATUS = "status"
    OTHER = "other"
