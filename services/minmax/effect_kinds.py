from enum import Enum


class EffectKind(str, Enum):
    STAT = "stat"
    COMBAT = "combat"
    RULE = "rule"
    