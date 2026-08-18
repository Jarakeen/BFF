from dataclasses import dataclass

from .role import Role


@dataclass(frozen=True)
class GroupEffect:
    source: str
    effect_type: str
    value: float
    affected_roles: frozenset[Role]
    affects_source: bool = True
    uptime: float = 1.0