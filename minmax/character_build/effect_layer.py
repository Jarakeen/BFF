from enum import Enum


class BarId(str, Enum):
    """Which of the two weapon bars this refers to."""

    FRONT = "front"
    BACK = "back"


class EffectLayer(str, Enum):
    """
    How an effect is produced, distinguishing mechanisms the ESO rules
    treat very differently even when the resulting effect looks similar:

    - CAST: only exists while the skill is actually cast/used.
    - SLOTTED: exists purely from the skill occupying a bar slot, with no
      cast required (e.g. a stat bonus from a slotted ability).
    - PASSIVE: granted by a class/skill-line passive, contingent on the
      skill line being owned and (sometimes) represented on the active bar.
    - PROC: produced by a set/item/enchantment under a trigger condition.
    - ULTIMATE: produced specifically by casting an ultimate ability.
    """

    CAST = "cast"
    SLOTTED = "slotted"
    PASSIVE = "passive"
    PROC = "proc"
    ULTIMATE = "ultimate"
