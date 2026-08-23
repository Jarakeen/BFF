from dataclasses import dataclass

from .effect_instance import EffectVariant


@dataclass(frozen=True)
class PassiveGrant:
    """
    Represents the chain:

        skill line owned -> (optionally: represented on active bar) -> passive

    This does not duplicate an effect onto a skill unless a passive
    genuinely grants it - the effect only lives here, on the passive
    itself, keyed to the skill line that grants it.
    """

    skill_line_id: str
    """The stable skill-line identity this passive belongs to."""

    effect: EffectVariant
    """The effect this passive grants once its conditions are met."""

    requires_active_bar_representation: bool = False
    """
    If True, this passive only applies while a skill from `skill_line_id`
    is slotted on the currently active bar (e.g. a class passive that
    rewards representing a skill line on the active bar, such as a
    Warden slotting a class-line ultimate purely for this reason). If
    False, the passive is always active once the skill line is owned,
    regardless of which bar is active.
    """
