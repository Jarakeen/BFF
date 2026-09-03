from __future__ import annotations

from dataclasses import dataclass, field


MAX_ATTRIBUTE_POINTS = 64
MAX_CHAMPION_POINTS = 3600
MAX_SLOTTED_PER_TREE = 4


@dataclass(frozen=True)
class AttributeAllocation:
    """The character's fixed pool of level-up attribute points."""

    health: int = 0
    magicka: int = 0
    stamina: int = 0

    def __post_init__(self) -> None:
        values = (self.health, self.magicka, self.stamina)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise TypeError("attribute allocations must be integers")
        if any(value < 0 for value in values):
            raise ValueError("attribute allocations cannot be negative")
        if self.total > MAX_ATTRIBUTE_POINTS:
            raise ValueError(f"attribute allocation cannot exceed {MAX_ATTRIBUTE_POINTS} points")

    @property
    def total(self) -> int:
        return self.health + self.magicka + self.stamina

    @property
    def is_complete(self) -> bool:
        return self.total == MAX_ATTRIBUTE_POINTS


@dataclass(frozen=True)
class ChampionPointState:
    """Purchased and active CP state relevant to calculation, not CP earning speed."""

    total: int = 0
    blue_slotted: int = 0
    red_slotted: int = 0
    green_slotted: int = 0

    def __post_init__(self) -> None:
        values = (self.total, self.blue_slotted, self.red_slotted, self.green_slotted)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise TypeError("champion point values must be integers")
        if self.total < 0 or self.total > MAX_CHAMPION_POINTS:
            raise ValueError(f"champion points must be between 0 and {MAX_CHAMPION_POINTS}")
        if any(value < 0 or value > MAX_SLOTTED_PER_TREE for value in values[1:]):
            raise ValueError(f"no CP tree may have more than {MAX_SLOTTED_PER_TREE} slotted abilities")


def _normalize_progression_map(value: dict[str, int] | None) -> dict[str, int] | None:
    if value is None:
        return None
    normalized: dict[str, int] = {}
    seen: set[str] = set()
    for raw_name, raw_rank in value.items():
        name = " ".join(str(raw_name or "").strip().split())
        key = name.casefold()
        if not name or key in seen:
            continue
        try:
            rank = int(raw_rank)
        except (TypeError, ValueError):
            continue
        if rank < 0:
            continue
        seen.add(key)
        normalized[name] = rank
    return normalized


@dataclass(frozen=True)
class CharacterProgression:
    """Character-owned progression state used by MinMax calculations.

    ``passive_ranks`` and ``passive_cp_points`` distinguish legacy/unknown
    state from explicit character facts. ``None`` means the caller has not
    supplied character-level progression. A mapping may contain zero, which is
    an explicit known-unpurchased value rather than an absence of evidence.
    """

    level: int = 50
    attributes: AttributeAllocation = AttributeAllocation()
    champion_points: ChampionPointState = ChampionPointState()
    owned_skill_lines: tuple[str, ...] = ()
    passive_ranks: dict[str, int] | None = None
    passive_cp_points: dict[str, int] | None = None
    _owned_skill_line_lookup: frozenset[str] = field(
        init=False, repr=False, compare=False, default_factory=frozenset
    )
    _passive_rank_lookup: dict[str, int] | None = field(
        init=False, repr=False, compare=False, default=None
    )
    _passive_cp_lookup: dict[str, int] | None = field(
        init=False, repr=False, compare=False, default=None
    )

    def __post_init__(self) -> None:
        if isinstance(self.level, bool) or not isinstance(self.level, int):
            raise TypeError("level must be an integer")
        if self.level < 1 or self.level > 50:
            raise ValueError("character level must be between 1 and 50")

        seen: set[str] = set()
        normalized: list[str] = []
        for value in self.owned_skill_lines:
            name = str(value or "").strip()
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            normalized.append(name)
        normalized_skill_lines = tuple(normalized)
        passive_ranks = _normalize_progression_map(self.passive_ranks)
        passive_cp_points = _normalize_progression_map(self.passive_cp_points)

        object.__setattr__(self, "owned_skill_lines", normalized_skill_lines)
        object.__setattr__(self, "passive_ranks", passive_ranks)
        object.__setattr__(self, "passive_cp_points", passive_cp_points)
        object.__setattr__(
            self,
            "_owned_skill_line_lookup",
            frozenset(name.casefold() for name in normalized_skill_lines),
        )
        object.__setattr__(
            self,
            "_passive_rank_lookup",
            None
            if passive_ranks is None
            else {name.casefold(): rank for name, rank in passive_ranks.items()},
        )
        object.__setattr__(
            self,
            "_passive_cp_lookup",
            None
            if passive_cp_points is None
            else {name.casefold(): points for name, points in passive_cp_points.items()},
        )

    def owns_skill_line(self, skill_line: str) -> bool:
        requested = str(skill_line or "").strip().casefold()
        return bool(requested) and requested in self._owned_skill_line_lookup

    @staticmethod
    def _lookup(mapping: dict[str, int] | None, name: str) -> int | None:
        if mapping is None:
            return None
        requested = " ".join(str(name or "").strip().split()).casefold()
        if not requested:
            return None
        return mapping.get(requested)

    def passive_rank(self, passive_name: str) -> int | None:
        return self._lookup(self._passive_rank_lookup, passive_name)

    def passive_cp_allocation(self, cp_name: str) -> int | None:
        return self._lookup(self._passive_cp_lookup, cp_name)

    @property
    def has_explicit_passive_progression(self) -> bool:
        return self.passive_ranks is not None

    @property
    def has_explicit_passive_cp_progression(self) -> bool:
        return self.passive_cp_points is not None
