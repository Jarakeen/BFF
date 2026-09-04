from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .saved_build_rotation_timing_audit import SavedBuildRotationTimingAudit


class HealerRotationTag(str, Enum):
    """Explicit healer-role purposes that may apply to one slotted action.

    Tags are deliberately non-exclusive. One skill can contribute to sustained
    healing and burst preparation, or to support maintenance and burst setup.
    The Rotation Engine must not infer these purposes from the skill name.
    """

    CRITICAL_HEALING = "critical_healing"
    BURST_PREPARATION = "burst_preparation"
    SUSTAINED_HEALING = "sustained_healing"
    SUPPORT_MAINTENANCE = "support_maintenance"
    DISCRETIONARY_FILLER = "discretionary_filler"
    MOVEMENT_UTILITY = "movement_utility"


@dataclass(frozen=True)
class HealerSkillPolicy:
    """Encounter-policy annotation for one exact saved-build bar slot."""

    bar: str
    slot: int
    skill_name: str
    tags: tuple[HealerRotationTag, ...]

    def __post_init__(self) -> None:
        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("healer policy bar must be 'front' or 'back'")
        object.__setattr__(self, "bar", bar)

        slot = int(self.slot)
        if slot < 1 or slot > 6:
            raise ValueError("healer policy slot must be between 1 and 6")
        object.__setattr__(self, "slot", slot)

        skill_name = str(self.skill_name or "").strip()
        if not skill_name:
            raise ValueError("healer policy skill name is required")
        object.__setattr__(self, "skill_name", skill_name)

        normalized: list[HealerRotationTag] = []
        seen: set[HealerRotationTag] = set()
        for raw_tag in self.tags:
            tag = raw_tag if isinstance(raw_tag, HealerRotationTag) else HealerRotationTag(str(raw_tag))
            if tag in seen:
                raise ValueError(f"duplicate healer rotation tag for {skill_name}: {tag.value}")
            seen.add(tag)
            normalized.append(tag)
        if not normalized:
            raise ValueError("healer policy requires at least one rotation tag")
        object.__setattr__(self, "tags", tuple(normalized))


@dataclass(frozen=True)
class ResolvedHealerSkillPolicy:
    policy: HealerSkillPolicy
    ability_id: int | None


@dataclass(frozen=True)
class HealerRotationPolicySet:
    character_name: str
    build_name: str
    policies: tuple[ResolvedHealerSkillPolicy, ...]
    unresolved: tuple[str, ...] = ()

    def with_tag(self, tag: HealerRotationTag) -> tuple[ResolvedHealerSkillPolicy, ...]:
        normalized = tag if isinstance(tag, HealerRotationTag) else HealerRotationTag(str(tag))
        return tuple(item for item in self.policies if normalized in item.policy.tags)


def _saved_bar_order(bar: str) -> int:
    """Return canonical saved-build bar order: front before back."""

    return 0 if bar == "front" else 1


def resolve_healer_rotation_policy(
    audit: SavedBuildRotationTimingAudit,
    policies: tuple[HealerSkillPolicy, ...],
    *,
    require_all_slotted: bool = True,
) -> HealerRotationPolicySet:
    """Validate explicit healer policy against the exact audited saved build.

    This layer does not infer tags. It only proves that caller-supplied policy
    still refers to skills actually occupying the declared bar/slot positions.
    By default every slotted action, including Ultimates, requires policy so a
    build edit cannot silently leave an unclassified action in the schedule.
    """

    if str(audit.role or "").strip().casefold() != "healer":
        raise ValueError(
            f"healer rotation policy requires a healer build, got {audit.role!r}"
        )

    audited_by_slot = {(item.bar, item.slot): item for item in audit.skills}
    policy_by_slot: dict[tuple[str, int], HealerSkillPolicy] = {}
    resolved: list[ResolvedHealerSkillPolicy] = []

    for policy in policies:
        key = (policy.bar, policy.slot)
        if key in policy_by_slot:
            raise ValueError(f"duplicate healer policy for {policy.bar} slot {policy.slot}")
        policy_by_slot[key] = policy

        audited = audited_by_slot.get(key)
        if audited is None:
            raise ValueError(
                f"healer policy does not match a slotted action: {policy.bar} slot {policy.slot}"
            )
        if audited.skill_name != policy.skill_name:
            raise ValueError(
                "healer policy skill does not match saved build: "
                f"{policy.bar} slot {policy.slot} expected {audited.skill_name!r}, got {policy.skill_name!r}"
            )
        resolved.append(
            ResolvedHealerSkillPolicy(
                policy=policy,
                ability_id=audited.duration_resolution.ability_id,
            )
        )

    unresolved: list[str] = []
    if require_all_slotted:
        for key, audited in audited_by_slot.items():
            if key not in policy_by_slot:
                unresolved.append(
                    f"{audited.bar} slot {audited.slot} {audited.skill_name}: healer rotation policy is required"
                )

    return HealerRotationPolicySet(
        character_name=audit.character_name,
        build_name=audit.build_name,
        policies=tuple(
            sorted(
                resolved,
                key=lambda item: (
                    _saved_bar_order(item.policy.bar),
                    item.policy.slot,
                ),
            )
        ),
        unresolved=tuple(unresolved),
    )
