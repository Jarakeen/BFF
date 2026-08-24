from dataclasses import dataclass, field

from .effects import EffectUnit
from .role import Role
from .support_effect_category import SupportEffectCategory
from .support_effect_trigger import SupportEffectTrigger
from .support_stacking import StackingBehavior
from .support_target_type import SupportTargetType


@dataclass(frozen=True)
class SupportEffect:
    """
    A reusable representation of a buff, debuff, status effect, or other
    group support effect.

    This is deliberately generic: nothing here is specific to a class,
    skill line, or role. A Warden's Frost Cloak, a healer's Major Courage,
    and a tank's Minor Breach are all just SupportEffect instances that
    differ in their field values, not in code paths.

    This models "this effect exists" - i.e. what a source can provide and
    under what conditions. Whether it actually contributes to a group (its
    real uptime against a specific roster, its real target coverage, its
    real damage/healing value) is a separate, future calculation. See
    `contributes_to_group` for the minimal exists-vs-matters distinction
    this foundation provides today.
    """

    source: str
    """What provides this effect, e.g. a skill, set, or item name."""

    name: str
    """The effect's display name, e.g. "Major Brutality", "Chilled"."""

    category: SupportEffectCategory
    """Whether this is a buff, debuff, status, or other."""

    effect_type: str
    """
    A short machine-readable effect type, matching the convention used by
    CombatEffect/GroupEffect elsewhere in minmax, e.g.
    "damage_amplification", "resistance_reduction", "resource_restore".
    """

    target_type: SupportTargetType
    """Who this effect actually lands on: self, ally, group, or enemy."""

    magnitude: float = 0.0
    """The effect's size, in `unit`."""

    unit: EffectUnit = EffectUnit.FLAT
    """Whether `magnitude` is a flat value or a percent."""

    target_count: int | None = None
    """How many targets this effect can cover at once, if limited."""

    range: float | None = None
    """How far this effect reaches from its source, in meters, if limited."""

    duration: float | None = None
    """How long a single application lasts, in seconds. None means passive/permanent."""

    scaling: str | None = None
    """
    Structural description of how this effect's magnitude/duration scale
    with something else (e.g. "1 second per 10 Ultimate spent"), if any.
    This is preserved as data only - nothing here evaluates the formula.
    """

    uptime: float = 1.0
    """Expected fraction of an encounter this effect is active, from 0.0 to 1.0."""

    stacking: StackingBehavior = StackingBehavior.UNIQUE
    """How repeated applications of this effect interact."""

    exclusivity_group: str | None = None
    """
    Named group this effect competes with, e.g. "major_brutality". Two
    effects sharing an exclusivity_group cannot both be meaningfully active
    at once (mirrors ESO's Major/Minor exclusivity).
    """

    conditions: tuple[str, ...] = ()
    """Named conditions that must hold for this effect to apply."""

    trigger: SupportEffectTrigger | None = None
    """
    How this effect is procced/applied, and what it leads to. Used to
    represent proc chains such as Frost -> Chilled -> Brittle without
    implementing proc resolution here.
    """

    damage_amplification: float | None = None
    """Percent increase to damage this effect contributes, if any."""

    resistance_reduction: float | None = None
    """Flat or percent resistance reduction this effect contributes, if any."""

    penetration: float | None = None
    """Penetration this effect contributes, if any."""

    healing_contribution: float | None = None
    """Healing done/received modifier this effect contributes, if any."""

    resource_type: str | None = None
    """Which resource this effect restores/affects, e.g. "magicka", if any."""

    resource_value: float | None = None
    """Amount of `resource_type` this effect contributes, if any."""

    applies_status: str | None = None
    """Name of a status effect this effect applies to its target, if any."""

    requires_status: str | None = None
    """Name of a status effect that must already be present, if any."""

    role_relevance: frozenset[Role] = field(default_factory=frozenset)
    """Which roles (DD/healer/tank) this effect is relevant to, if known."""

    def __post_init__(self) -> None:
        if not 0.0 <= self.uptime <= 1.0:
            raise ValueError(
                "SupportEffect uptime must be between 0 and 1."
            )

        if self.target_count is not None and self.target_count < 0:
            raise ValueError(
                "SupportEffect target_count cannot be negative."
            )

        if self.duration is not None and self.duration < 0:
            raise ValueError(
                "SupportEffect duration cannot be negative."
            )

    def contributes_to_group(self) -> bool:
        """
        Whether this effect at least has a chance to matter beyond its own
        source, as distinct from merely existing.

        This is intentionally minimal - a self-only effect, or one with no
        uptime, never contributes. Everything else is a candidate. The real
        group-DPS/HPS contribution calculation is future work and belongs
        in a separate module, not in the data model itself.
        """
        if self.uptime <= 0.0:
            return False

        if self.target_type == SupportTargetType.SELF:
            return False

        return True
