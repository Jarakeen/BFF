from dataclasses import dataclass

from .role import Role


@dataclass(frozen=True)
class RoleRequirement:
    role: Role
    count: int