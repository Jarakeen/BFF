from dataclasses import dataclass, field

from .effect_instance import EffectVariant


@dataclass(frozen=True)
class SlottedSkill:
    """
    One skill occupying one actual bar slot.

    A bar slot is a finite resource: this represents what is placed in
    it, not just "a skill exists somewhere in the build". A skill can
    have value simply from being slotted, whether or not it is ever cast
    - `is_cast` and `effects` (tagged by EffectLayer) are what let a
    future evaluator tell the difference, instead of assuming every
    slotted skill is only valuable when cast.
    """

    skill_id: str
    """Stable snake_case skill identity."""

    skill_line_id: str
    """Which skill line this skill belongs to (class/weapon/guild/world/...)."""

    is_ultimate: bool = False

    is_cast: bool = False
    """
    Whether this build's rotation actually casts this skill. A slotted
    skill with is_cast=False is a legitimate "flex"/support/passive slot,
    not a wasted one - see `effects` for what it still contributes.
    """

    requires_active_bar: bool = True
    """
    Whether this skill's SLOTTED-layer effects only count while the bar
    it occupies is the currently active bar (the common case), versus
    counting simply by being slotted on either bar.
    """

    effects: tuple[EffectVariant, ...] = field(default_factory=tuple)
    """
    The mechanical effects this slot can produce. A CAST-layer effect
    only matters if `is_cast` is True; a SLOTTED-layer effect matters
    purely from occupying the slot, subject to `requires_active_bar`.
    """
