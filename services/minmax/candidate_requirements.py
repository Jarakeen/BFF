from dataclasses import dataclass
from .roster_types import Role


@dataclass(frozen=True)
class CandidateRequirement:
    role: Role
    count: int = 1
    required_class: str | None = None
    minimum_personal_damage: float | None = None

    def matches(self, candidate) -> bool:
        if candidate.role != self.role:
            return False

        if (
            self.required_class is not None
            and candidate.class_name != self.required_class
        ):
            return False

        if (
            self.minimum_personal_damage is not None
            and candidate.personal_damage < self.minimum_personal_damage
        ):
            return False

        return True