from __future__ import annotations

import re

from models.build_model import PlayerBuild

from .build_candidate import BuildCandidate, BuildChange
from .provisioning_static_repository import ProvisioningStaticRepository
from .resource_costs import ResourceType
from .stat_ids import StatId


_RESOURCE_STATS = {
    ResourceType.HEALTH: frozenset({StatId.MAX_HEALTH, StatId.HEALTH_RECOVERY}),
    ResourceType.MAGICKA: frozenset({StatId.MAX_MAGICKA, StatId.MAGICKA_RECOVERY}),
    ResourceType.STAMINA: frozenset({StatId.MAX_STAMINA, StatId.STAMINA_RECOVERY}),
}


def provisioning_candidate_resources(
    candidate: BuildCandidate,
    provisioning_repository: ProvisioningStaticRepository,
) -> tuple[ResourceType, ...]:
    """Return primary resource channels touched by one provisioning candidate.

    Classification is based on resolved canonical stat effects, not item naming
    conventions. Mixed food/drinks therefore belong to every resource channel
    they actually affect.
    """

    effects, unresolved = provisioning_repository.resolve(candidate.candidate_build.Food)
    if unresolved:
        return ()
    stats = {effect.stat for effect in effects if effect.stat is not None}
    return tuple(
        resource
        for resource in (ResourceType.HEALTH, ResourceType.MAGICKA, ResourceType.STAMINA)
        if stats & _RESOURCE_STATS[resource]
    )


def _resource_effect_values(
    name: str,
    *,
    resource: ResourceType,
    provisioning_repository: ProvisioningStaticRepository,
) -> tuple[dict[StatId, float], bool]:
    effects, unresolved = provisioning_repository.resolve(name)
    if unresolved:
        return {}, False
    relevant = _RESOURCE_STATS[resource]
    return (
        {
            effect.stat: float(effect.value)
            for effect in effects
            if effect.stat in relevant
        },
        True,
    )


def filter_food_candidates_for_resource(
    candidates: tuple[BuildCandidate, ...],
    *,
    resource: ResourceType,
    provisioning_repository: ProvisioningStaticRepository,
    baseline_food: str | None = None,
) -> tuple[BuildCandidate, ...]:
    """Keep provisioning candidates that can improve a failing resource channel.

    Without ``baseline_food`` this preserves the original conservative rule:
    keep every candidate that changes the requested maximum pool or recovery.

    When a resolved baseline food is supplied, keep only candidates that improve
    at least one requested sustain input relative to that baseline. A candidate
    whose requested maximum pool and recovery are both unchanged or lower cannot
    repair a proven failing sustain timeline under the current static one-food
    model. Mixed candidates remain eligible when either dimension improves,
    because a gain in one input can still outweigh a loss in the other.

    Unknown baseline evidence fails open to the conservative resource-touching
    rule rather than dropping candidates on incomplete information.
    """

    if resource not in _RESOURCE_STATS:
        return candidates

    touching = tuple(
        candidate
        for candidate in candidates
        if resource in provisioning_candidate_resources(candidate, provisioning_repository)
    )
    if not baseline_food:
        return touching

    baseline_values, baseline_resolved = _resource_effect_values(
        baseline_food,
        resource=resource,
        provisioning_repository=provisioning_repository,
    )
    if not baseline_resolved:
        return touching

    relevant_stats = _RESOURCE_STATS[resource]
    result: list[BuildCandidate] = []
    for candidate in touching:
        candidate_values, candidate_resolved = _resource_effect_values(
            candidate.candidate_build.Food,
            resource=resource,
            provisioning_repository=provisioning_repository,
        )
        if not candidate_resolved:
            continue
        if any(
            candidate_values.get(stat, 0.0) > baseline_values.get(stat, 0.0)
            for stat in relevant_stats
        ):
            result.append(candidate)
    return tuple(result)


def _normalized_description(
    name: str,
    provisioning_repository: ProvisioningStaticRepository,
) -> str | None:
    resolver = getattr(provisioning_repository, "description", None)
    if not callable(resolver):
        return None
    value = resolver(name)
    if value is None:
        return None
    return " ".join(str(value).split()).casefold()


def _effect_signature(effects) -> tuple[tuple[str, str, float, str], ...]:
    rows: list[tuple[str, str, float, str]] = []
    for effect in effects:
        stat = getattr(effect, "stat", None)
        operation = getattr(effect, "operation", None)
        unit = getattr(effect, "unit", None)
        rows.append(
            (
                str(getattr(stat, "value", stat)),
                str(getattr(operation, "value", operation)),
                float(getattr(effect, "value", 0.0)),
                str(getattr(unit, "value", unit)),
            )
        )
    return tuple(sorted(rows))


def _provisioning_equivalence_signature(
    name: str,
    effects,
    provisioning_repository: ProvisioningStaticRepository,
) -> tuple[str | None, tuple[tuple[str, str, float, str], ...]]:
    """Return a conservative exact-equivalence signature for evaluation reuse.

    Parsed stat effects alone are not sufficient because two consumables could
    share the currently mapped stat package while carrying different extra
    tooltip mechanics. Include normalized canonical tooltip text when the
    repository exposes it so those items remain separate.
    """

    return (
        _normalized_description(name, provisioning_repository),
        _effect_signature(effects),
    )


def enumerate_food_candidates(
    *,
    baseline_build: PlayerBuild,
    character_id: str,
    baseline_build_id: str,
    provisioning_repository: ProvisioningStaticRepository,
    candidate_source: str = "phase12:food",
) -> tuple[BuildCandidate, ...]:
    """Enumerate deterministic one-change food/drink candidates.

    Candidate names come from the canonical provisioning repository. A listed
    food is included only when its static character-sheet effects resolve
    cleanly; dynamic or currently unmapped consumables stay out of the bounded
    Phase 12 search rather than becoming knowingly UNKNOWN candidates.

    Exact canonical mechanical equivalents are represented once. This keeps
    the optimizer from rebuilding the same stat/recovery state for hundreds of
    differently named consumables while preserving distinct tooltip mechanics.
    """

    current = provisioning_repository.canonical_name(baseline_build.Food)
    candidates: list[BuildCandidate] = []
    seen_signatures: set[
        tuple[str | None, tuple[tuple[str, str, float, str], ...]]
    ] = set()

    for listed_name in provisioning_repository.list_names():
        name = provisioning_repository.canonical_name(listed_name)
        if not name or name.casefold() == current.casefold():
            continue
        effects, unresolved = provisioning_repository.resolve(name)
        if unresolved or not effects:
            continue

        signature = _provisioning_equivalence_signature(
            name,
            effects,
            provisioning_repository,
        )
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        candidate_build = PlayerBuild.from_dict(baseline_build.to_dict())
        candidate_build.Food = name
        candidates.append(
            BuildCandidate.from_build(
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                candidate_id=f"{baseline_build_id}:food:{_candidate_token(name)}",
                candidate_build=candidate_build,
                changes=(
                    BuildChange.from_values(
                        path="Food",
                        before=current,
                        after=name,
                        source=candidate_source,
                    ),
                ),
                candidate_source=candidate_source,
            )
        )

    return tuple(candidates)


def _candidate_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")
    if not token:
        raise ValueError("Food candidate name cannot produce an empty candidate id.")
    return token
