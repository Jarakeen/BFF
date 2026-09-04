from __future__ import annotations

from dataclasses import dataclass

from .rotation_demand_window import RotationDemandWindow


_BAR_ORDER = {"front": 0, "back": 1}


@dataclass(frozen=True)
class AbilityPriorityEntry:
    """Base priority for one exact saved-bar ability.

    Lower numeric values are higher priority. Equal values deliberately mean the
    abilities share one priority tier; canonical bar/slot order is used only for
    deterministic presentation, not as a hidden gameplay preference.
    """

    bar: str
    slot: int
    skill_name: str
    priority: int

    def __post_init__(self) -> None:
        bar = str(self.bar or "").strip().lower()
        if bar not in _BAR_ORDER:
            raise ValueError("ability priority bar must be front or back")
        object.__setattr__(self, "bar", bar)

        slot = int(self.slot)
        if slot < 1 or slot > 6:
            raise ValueError("ability priority slot must be between 1 and 6")
        object.__setattr__(self, "slot", slot)

        name = str(self.skill_name or "").strip()
        if not name:
            raise ValueError("ability priority skill name is required")
        object.__setattr__(self, "skill_name", name)

        priority = int(self.priority)
        if priority < 0:
            raise ValueError("ability priority cannot be negative")
        object.__setattr__(self, "priority", priority)


@dataclass(frozen=True)
class AbilityPriorityOverride:
    """Encounter-demand override for one exact saved-bar ability."""

    demand_name: str
    bar: str
    slot: int
    skill_name: str
    priority: int
    reason: str | None = None

    def __post_init__(self) -> None:
        demand = str(self.demand_name or "").strip()
        if not demand:
            raise ValueError("ability priority override demand name is required")
        object.__setattr__(self, "demand_name", demand)

        base = AbilityPriorityEntry(
            bar=self.bar,
            slot=self.slot,
            skill_name=self.skill_name,
            priority=self.priority,
        )
        object.__setattr__(self, "bar", base.bar)
        object.__setattr__(self, "slot", base.slot)
        object.__setattr__(self, "skill_name", base.skill_name)
        object.__setattr__(self, "priority", base.priority)

        if self.reason is not None:
            reason = str(self.reason).strip()
            object.__setattr__(self, "reason", reason or None)


@dataclass(frozen=True)
class ResolvedAbilityPriority:
    entry: AbilityPriorityEntry
    effective_priority: int
    override: AbilityPriorityOverride | None = None


@dataclass(frozen=True)
class AbilityPriorityList:
    """Role-neutral base priorities plus explicit encounter-demand overrides."""

    character_name: str
    build_name: str
    role: str
    entries: tuple[AbilityPriorityEntry, ...]
    overrides: tuple[AbilityPriorityOverride, ...] = ()

    def __post_init__(self) -> None:
        character = str(self.character_name or "").strip()
        build = str(self.build_name or "").strip()
        role = str(self.role or "").strip()
        if not character:
            raise ValueError("ability priority character name is required")
        if not build:
            raise ValueError("ability priority build name is required")
        if not role:
            raise ValueError("ability priority role is required")
        object.__setattr__(self, "character_name", character)
        object.__setattr__(self, "build_name", build)
        object.__setattr__(self, "role", role)

        by_slot: dict[tuple[str, int], AbilityPriorityEntry] = {}
        for entry in self.entries:
            key = (entry.bar, entry.slot)
            if key in by_slot:
                raise ValueError(
                    f"duplicate ability priority entry for {entry.bar} slot {entry.slot}"
                )
            by_slot[key] = entry

        seen_overrides: set[tuple[str, str, int]] = set()
        for override in self.overrides:
            key = (override.demand_name, override.bar, override.slot)
            if key in seen_overrides:
                raise ValueError(
                    "duplicate ability priority override for "
                    f"{override.demand_name}: {override.bar} slot {override.slot}"
                )
            seen_overrides.add(key)

            entry = by_slot.get((override.bar, override.slot))
            if entry is None:
                raise ValueError(
                    "ability priority override targets an unlisted saved slot: "
                    f"{override.bar} slot {override.slot}"
                )
            if entry.skill_name != override.skill_name:
                raise ValueError(
                    "ability priority override skill does not match base entry: "
                    f"{override.skill_name!r} != {entry.skill_name!r}"
                )

    def resolve(
        self,
        demand: RotationDemandWindow | None = None,
    ) -> tuple[ResolvedAbilityPriority, ...]:
        """Return deterministic effective priorities for the current demand.

        No encounter means base priorities only. When a demand is supplied, only
        overrides with the exact demand name apply. Equal effective priorities
        remain equal; bar/slot ordering merely stabilizes output presentation.
        """

        override_by_slot: dict[tuple[str, int], AbilityPriorityOverride] = {}
        if demand is not None:
            override_by_slot = {
                (override.bar, override.slot): override
                for override in self.overrides
                if override.demand_name == demand.name
            }

        resolved = tuple(
            ResolvedAbilityPriority(
                entry=entry,
                effective_priority=(
                    override_by_slot[(entry.bar, entry.slot)].priority
                    if (entry.bar, entry.slot) in override_by_slot
                    else entry.priority
                ),
                override=override_by_slot.get((entry.bar, entry.slot)),
            )
            for entry in self.entries
        )
        return tuple(
            sorted(
                resolved,
                key=lambda item: (
                    item.effective_priority,
                    _BAR_ORDER[item.entry.bar],
                    item.entry.slot,
                ),
            )
        )
