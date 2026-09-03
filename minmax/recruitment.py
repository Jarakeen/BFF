from __future__ import annotations

from dataclasses import dataclass

from .roster_types import Role


@dataclass(frozen=True)
class RecruitmentRequirement:
    """An open roster requirement, never a fabricated player."""

    slot_id: str
    role: Role
    role_label: str
    minimum_parse_damage: float | None = None
    minimum_experience: str = "Endgame trial experience"
    required_capabilities: tuple[str, ...] = ()
    hypothetical: bool = True

    def __post_init__(self) -> None:
        if not self.slot_id.strip():
            raise ValueError("Recruitment requirement slot_id cannot be empty")
        if not self.role_label.strip():
            raise ValueError("Recruitment requirement role_label cannot be empty")
        if self.minimum_parse_damage is not None and self.minimum_parse_damage < 0:
            raise ValueError("minimum_parse_damage cannot be negative")
        if self.role is not Role.DD and self.minimum_parse_damage is not None:
            raise ValueError("minimum_parse_damage is only valid for DD requirements")

    @property
    def qualification_summary(self) -> str:
        requirements: list[str] = []
        if self.minimum_parse_damage is not None:
            requirements.append(f"{self.minimum_parse_damage / 1000:.0f}K DPS parse")
        if self.minimum_experience:
            requirements.append(self.minimum_experience)
        requirements.extend(self.required_capabilities)
        return " • ".join(requirements) or "Encounter requirements pending"


@dataclass(frozen=True)
class RecruitmentPlan:
    """Open requirements needed to complete a roster."""

    party_size: int
    real_member_count: int
    requirements: tuple[RecruitmentRequirement, ...]

    @property
    def open_slot_count(self) -> int:
        return len(self.requirements)

    @property
    def complete_slot_count(self) -> int:
        return self.real_member_count + self.open_slot_count


class RecruitmentPlanner:
    """Creates honest open-slot specifications around known players."""

    def __init__(
        self,
        *,
        dd_minimum_parse_damage: float = 165_000.0,
        minimum_experience: str = "Endgame trial experience",
    ) -> None:
        if dd_minimum_parse_damage < 0:
            raise ValueError("dd_minimum_parse_damage cannot be negative")
        self.dd_minimum_parse_damage = dd_minimum_parse_damage
        self.minimum_experience = minimum_experience

    @staticmethod
    def role_for_label(role_label: str) -> Role:
        normalized = role_label.strip().casefold()
        if "tank" in normalized:
            return Role.TANK
        if "heal" in normalized:
            return Role.HEALER
        if normalized.startswith("dd") or "damage" in normalized:
            return Role.DD
        raise ValueError(f"Unsupported roster role label: {role_label!r}")

    def create_requirement(
        self,
        *,
        slot_id: str,
        role_label: str,
        required_capabilities: tuple[str, ...] = (),
    ) -> RecruitmentRequirement:
        role = self.role_for_label(role_label)
        return RecruitmentRequirement(
            slot_id=slot_id,
            role=role,
            role_label=role_label,
            minimum_parse_damage=(
                self.dd_minimum_parse_damage if role is Role.DD else None
            ),
            minimum_experience=self.minimum_experience,
            required_capabilities=required_capabilities,
        )

    def build_plan(
        self,
        *,
        party_size: int,
        real_member_count: int,
        open_role_labels: tuple[str, ...],
    ) -> RecruitmentPlan:
        if party_size < 1:
            raise ValueError("party_size must be positive")
        if real_member_count < 0:
            raise ValueError("real_member_count cannot be negative")
        if real_member_count + len(open_role_labels) != party_size:
            raise ValueError(
                "Real members and open recruitment slots must equal party_size"
            )

        requirements = tuple(
            self.create_requirement(
                slot_id=f"recruitment-{index}",
                role_label=role_label,
            )
            for index, role_label in enumerate(open_role_labels, start=1)
        )
        return RecruitmentPlan(
            party_size=party_size,
            real_member_count=real_member_count,
            requirements=requirements,
        )
