from __future__ import annotations

from dataclasses import dataclass

from minmax.effects import EffectOperation
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId


_FOOD_STAT_BY_OBJECTIVE: dict[str, StatId] = {
    "max_health": StatId.MAX_HEALTH,
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
    "health_recovery": StatId.HEALTH_RECOVERY,
    "magicka_recovery": StatId.MAGICKA_RECOVERY,
    "stamina_recovery": StatId.STAMINA_RECOVERY,
}


@dataclass(frozen=True)
class ExtremeFoodWinners:
    objective_key: str
    stat: StatId | None
    value: float
    winners: tuple[str, ...]
    representative: str
    selected_food: str

    @property
    def relevant(self) -> bool:
        return self.stat is not None

    @property
    def selected_is_winner(self) -> bool:
        selected = self.selected_food.casefold()
        return bool(selected) and any(name.casefold() == selected for name in self.winners)

    @property
    def tied(self) -> bool:
        return len(self.winners) > 1


def _flat_stat_value(
    name: str,
    *,
    stat: StatId,
    repository: ProvisioningStaticRepository,
) -> float | None:
    effects, unresolved = repository.resolve(name)
    if unresolved:
        return None
    return sum(
        float(effect.value)
        for effect in effects
        if effect.stat is stat and effect.operation is EffectOperation.ADD
    )


def extreme_food_winners(
    objective_key: str,
    *,
    selected_food: str = "",
    repository: ProvisioningStaticRepository,
) -> ExtremeFoodWinners:
    """Return every canonical food tied for the largest relevant static effect.

    Candidate optimization is allowed to collapse mechanically equivalent foods
    for speed. Result presentation is not. Players may have several recipes that
    provide the same maximum Health/Magicka/Stamina or recovery value, so expose
    all canonical co-winners while retaining one deterministic representative.
    """

    key = str(objective_key or "").strip().casefold()
    stat = _FOOD_STAT_BY_OBJECTIVE.get(key)
    selected = repository.canonical_name(selected_food)
    if stat is None:
        return ExtremeFoodWinners(key, None, 0.0, (), "", selected)

    values: list[tuple[str, float]] = []
    for listed_name in repository.list_names():
        name = repository.canonical_name(listed_name)
        value = _flat_stat_value(name, stat=stat, repository=repository)
        if value is None or value <= 0.0:
            continue
        values.append((name, value))

    if not values:
        return ExtremeFoodWinners(key, stat, 0.0, (), "", selected)

    maximum = max(value for _, value in values)
    winners = tuple(
        sorted(
            {name for name, value in values if abs(value - maximum) <= 1e-9},
            key=lambda value: (value.casefold(), value),
        )
    )
    representative = next(
        (name for name in winners if name.casefold() == selected.casefold()),
        winners[0] if winners else "",
    )
    return ExtremeFoodWinners(key, stat, maximum, winners, representative, selected)


def format_extreme_food_result(result: ExtremeFoodWinners) -> tuple[str, str | None]:
    """Return the primary Food row plus an optional co-winner detail row."""

    if not result.relevant:
        return "No food improves this exact objective", None
    if not result.winners:
        return "No resolved canonical food improves this objective", None

    if not result.selected_is_winner:
        primary = (
            f"MAX FOOD NOT APPLIED • use {result.representative} "
            f"({result.value:g} {result.stat.value.replace('_', ' ').title()})"
        )
    else:
        primary = result.representative
        if result.tied:
            primary += f" • {len(result.winners)}-way tie"

    detail = ", ".join(result.winners) if result.tied else None
    return primary, detail
