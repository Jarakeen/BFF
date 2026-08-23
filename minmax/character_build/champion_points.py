from dataclasses import dataclass, field

from .effect_instance import EffectVariant


@dataclass(frozen=True)
class ChampionPointAllocation:
    """
    Points invested in one Champion Point node.

    `node_id` is the stable snake_case identity of the CP star/slottable;
    `points` is its numeric variant. The two are never conflated.
    """

    node_id: str
    points: int = 0

    effects: tuple[EffectVariant, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.points < 0:
            raise ValueError("ChampionPointAllocation.points cannot be negative.")
