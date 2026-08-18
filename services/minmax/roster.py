from .group_effects import GroupEffect
from .roster_types import Role
from dataclasses import dataclass, field
from .candidate_requirements import CandidateRequirement
from .roster_constraints import RoleRequirement

@dataclass(frozen=True)
class RosterSlot:
    role: Role
    class_name: str | None = None
    archetype: str | None = None
    locked: bool = False


@dataclass(frozen=True)
class RosterCandidate:
    name: str
    role: Role
    class_name: str

    personal_damage: float = 0.0
    support_value: float = 0.0
    survivability: float = 0.0
    mechanic_value: float = 0.0
    group_effects: tuple[GroupEffect, ...] = ()
    

@dataclass
class RosterRequest:
    trial: str
    party_size: int
    objective: str
    fixed_slots: list[RosterSlot]

    role_requirements: tuple[RoleRequirement, ...] = ()

    candidate_requirements: list[CandidateRequirement] = field(
        default_factory=list
    )

    @property
    def remaining_slots(self) -> int:
        return self.party_size - len(self.fixed_slots)
