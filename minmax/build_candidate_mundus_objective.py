from __future__ import annotations

from minmax.build_candidate import BuildCandidate
from minmax.mundus_repository import MundusRepository
from minmax.stat_ids import StatId


_UNMODELED_DAMAGE_OBJECTIVE_STATS = frozenset(
    {
        StatId.MAX_MAGICKA.value,
        StatId.MAX_STAMINA.value,
    }
)


def damage_mundus_objective_unresolved(
    candidate: BuildCandidate,
    mundus_repository: MundusRepository,
) -> tuple[str, ...]:
    """Flag offensive resource scaling absent from the single-event DD metric."""

    mundus_name = str(candidate.candidate_build.Mundus or "").strip()
    if not mundus_name:
        return ()

    unresolved: list[str] = []
    for record in mundus_repository.get_records(mundus_name):
        if record.stat_id not in _UNMODELED_DAMAGE_OBJECTIVE_STATS:
            continue
        unresolved.append(
            f"{mundus_name}: {record.stat_id} is not included in the selected "
            "single-event damage metric; ability resource scaling is unresolved"
        )
    return tuple(unresolved)


_UNMODELED_HEALING_OBJECTIVE_STATS = frozenset(
    {
        StatId.CRITICAL_CHANCE.value,
        StatId.CRITICAL_HEALING.value,
    }
)


def healing_mundus_objective_unresolved(
    candidate: BuildCandidate,
    mundus_repository: MundusRepository,
) -> tuple[str, ...]:
    """Return Mundus dimensions absent from modeled healing potency.

    The current Phase 12 healing objective sums verified non-critical healing
    components. Critical chance and critical-healing magnitude require an
    expected-critical-value model before candidates changing those stats can be
    compared honestly against Ritual, Mage, Apprentice, and other stones.
    """

    mundus_name = str(candidate.candidate_build.Mundus or "").strip()
    if not mundus_name:
        return ()

    unresolved: list[str] = []
    for record in mundus_repository.get_records(mundus_name):
        if record.stat_id not in _UNMODELED_HEALING_OBJECTIVE_STATS:
            continue
        unresolved.append(
            f"{mundus_name}: {record.stat_id} is not included in modeled healing potency; "
            "expected critical healing is unresolved"
        )
    return tuple(unresolved)
