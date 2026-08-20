from dataclasses import dataclass


@dataclass(frozen=True)
class BuildGearSet:
    """A gear set currently equipped by a build."""

    set_id: int
    piece_count: int
    