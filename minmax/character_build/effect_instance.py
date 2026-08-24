from dataclasses import dataclass

from ..support_effect_category import SupportEffectCategory
from ..support_stacking import StackingBehavior
from ..support_target_type import SupportTargetType
from .effect_layer import BarId, EffectLayer


@dataclass(frozen=True)
class EffectVariant:
    """
    One concrete instance of a named effect.

    `name` is the stable logical identity (e.g. "major_slayer",
    "major_brittle", "weapon_spell_damage") - snake_case, and it is the
    ONLY field that may be used to recognize "this is the same effect as
    that one". Every other field is a numeric/contextual variant of that
    identity and must never be used as a substitute for it. Two
    EffectVariants with the same `name` but different `magnitude`,
    `source`, or `active_bar` are still the same logical effect supplied
    two different ways - callers compare on `name`, never on magnitude.

    This generalizes the identity/magnitude split already used by
    SupportEffect (name vs magnitude) to the rest of the character-build
    model: cast/slotted/passive/proc/ultimate effects all share this same
    shape instead of each inventing their own value-as-identity encoding.
    """

    name: str
    """Stable snake_case logical identity. Never a number."""

    layer: EffectLayer
    """How this effect instance is produced."""

    source: str
    """What produces it: a skill, set, glyph, passive, or item name."""

    magnitude: float | None = None
    duration: float | None = None
    chance: float | None = None
    cooldown: float | None = None
    target_count: int | None = None
    range: float | None = None
    scaling: str | None = None
    condition: str | None = None
    target: str | None = None

    active_bar: BarId | None = None
    """
    Which bar this effect instance requires to be active, if any. None
    means it does not depend on which bar is currently active.
    """

    trigger: str | None = None
    """Named trigger this instance requires, if any (e.g. an ultimate cast)."""

    target_type: SupportTargetType | None = None
    """
    Who this effect actually lands on: self/ally/group/enemy. None means
    not yet classified - conversion to SupportEffect treats an
    unclassified effect as SELF rather than guessing it contributes to
    group support.
    """

    category: SupportEffectCategory | None = None
    """Whether this is a buff/debuff/status/other, if known."""

    stacking: StackingBehavior | None = None
    """How repeated applications of this effect interact, if known."""

    exclusivity_group: str | None = None
    """Named group this effect competes with (mirrors Major/Minor exclusivity)."""

    eligible: bool = True
    """
    Whether this instance's own condition and any REQUIRES relationships
    have actually been satisfied against a known condition context.

    Defaults to True: an effect with nothing gating it, or resolved with
    no condition context supplied at all, is eligible by default (this
    preserves every existing call site that never evaluates conditions).
    When a context IS supplied and a condition/prerequisite is not met,
    this becomes False - the instance is kept, not discarded, so its
    evidence (source, magnitude, condition, etc.) remains inspectable by
    callers that want to know *why* something isn't contributing, rather
    than only that it silently isn't there. See
    `effect_relationship.apply_relationships`.
    """

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("EffectVariant.name must be a non-empty identity.")

        if self.chance is not None and not 0.0 <= self.chance <= 1.0:
            raise ValueError("EffectVariant.chance must be between 0 and 1.")

    def is_available_on(self, active_bar: BarId) -> bool:
        """Whether this instance's bar requirement is satisfied."""
        return self.active_bar is None or self.active_bar == active_bar
