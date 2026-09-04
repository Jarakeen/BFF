from __future__ import annotations

from dataclasses import dataclass

from .healer_rotation_policy import (
    HealerRotationPolicySet,
    HealerRotationTag,
    ResolvedHealerSkillPolicy,
)
from .rotation_demand_window import RotationDemandKind, RotationDemandWindow


@dataclass(frozen=True)
class HealerDemandPolicy:
    """Explicit healer-tag treatment for one encounter demand window.

    Protected tags identify actions that policy says must not be sacrificed for
    reserve protection around this demand. Discretionary tags identify actions
    eligible for later reserve-protection analysis. Unmatched actions remain
    neutral rather than being silently promoted or sacrificed.
    """

    demand_name: str
    protected_tags: tuple[HealerRotationTag, ...]
    discretionary_tags: tuple[HealerRotationTag, ...] = ()

    def __post_init__(self) -> None:
        name = str(self.demand_name or "").strip()
        if not name:
            raise ValueError("healer demand policy requires a demand name")
        object.__setattr__(self, "demand_name", name)

        protected = _normalize_tags(self.protected_tags, label="protected")
        discretionary = _normalize_tags(self.discretionary_tags, label="discretionary")
        overlap = set(protected) & set(discretionary)
        if overlap:
            rendered = ", ".join(sorted(tag.value for tag in overlap))
            raise ValueError(
                f"healer demand policy tags cannot be both protected and discretionary: {rendered}"
            )
        object.__setattr__(self, "protected_tags", protected)
        object.__setattr__(self, "discretionary_tags", discretionary)


@dataclass(frozen=True)
class HealerDemandPolicyAssessment:
    demand: RotationDemandWindow
    protected: tuple[ResolvedHealerSkillPolicy, ...]
    discretionary: tuple[ResolvedHealerSkillPolicy, ...]
    neutral: tuple[ResolvedHealerSkillPolicy, ...]


def _normalize_tags(
    tags: tuple[HealerRotationTag, ...],
    *,
    label: str,
) -> tuple[HealerRotationTag, ...]:
    normalized: list[HealerRotationTag] = []
    seen: set[HealerRotationTag] = set()
    for raw_tag in tags:
        tag = raw_tag if isinstance(raw_tag, HealerRotationTag) else HealerRotationTag(str(raw_tag))
        if tag in seen:
            raise ValueError(f"duplicate {label} healer demand tag: {tag.value}")
        seen.add(tag)
        normalized.append(tag)
    return tuple(normalized)


def assess_healer_demand_policy(
    *,
    policy_set: HealerRotationPolicySet,
    demand: RotationDemandWindow,
    demand_policy: HealerDemandPolicy,
) -> HealerDemandPolicyAssessment:
    """Classify exact saved healer actions for one explicit encounter demand."""

    if demand.kind is not RotationDemandKind.HEALING:
        raise ValueError(
            f"healer demand policy requires a healing demand, got {demand.kind.value}"
        )
    if demand.name != demand_policy.demand_name:
        raise ValueError(
            "healer demand policy does not match demand window: "
            f"{demand_policy.demand_name!r} != {demand.name!r}"
        )
    if policy_set.unresolved:
        raise ValueError(
            "healer demand policy requires a fully classified healer rotation policy"
        )

    protected_tags = set(demand_policy.protected_tags)
    discretionary_tags = set(demand_policy.discretionary_tags)

    protected: list[ResolvedHealerSkillPolicy] = []
    discretionary: list[ResolvedHealerSkillPolicy] = []
    neutral: list[ResolvedHealerSkillPolicy] = []

    for item in policy_set.policies:
        tags = set(item.policy.tags)
        is_protected = bool(tags & protected_tags)
        is_discretionary = bool(tags & discretionary_tags)
        if is_protected and is_discretionary:
            raise ValueError(
                "healer action matches both protected and discretionary demand policy: "
                f"{item.policy.skill_name} ({item.policy.bar} slot {item.policy.slot})"
            )
        if is_protected:
            protected.append(item)
        elif is_discretionary:
            discretionary.append(item)
        else:
            neutral.append(item)

    return HealerDemandPolicyAssessment(
        demand=demand,
        protected=tuple(protected),
        discretionary=tuple(discretionary),
        neutral=tuple(neutral),
    )
