from dataclasses import dataclass


@dataclass(frozen=True)
class SupportEffectTrigger:
    """
    Describes how a support effect is procced/applied, and what it leads to.

    This is intentionally a data-only description. It lets a SupportEffect
    say "I am applied by this trigger, with this chance, under this
    condition, and I produce this resulting effect/status" without any
    engine attempting to resolve procs yet. That is future work.

    This is what lets a chain such as:

        Frost effect -> proc rule -> Chilled -> Brittle

    be represented structurally: each link is a SupportEffect whose
    `trigger` names the effect/status before it, and whose
    `resulting_effect`/`resulting_status` names what comes next.
    """

    trigger: str
    """What causes this effect to apply, e.g. "on_direct_damage", "on_light_attack"."""

    chance: float = 1.0
    """Probability the trigger results in application, from 0.0 to 1.0."""

    condition: str | None = None
    """An additional named condition that must hold, e.g. "target_is_chilled"."""

    resulting_effect: str | None = None
    """Name of another support effect this trigger applies, if any."""

    resulting_status: str | None = None
    """Name of a status effect this trigger applies, e.g. "Chilled", "Brittle"."""

    def __post_init__(self) -> None:
        if not 0.0 <= self.chance <= 1.0:
            raise ValueError(
                "SupportEffectTrigger chance must be between 0 and 1."
            )
