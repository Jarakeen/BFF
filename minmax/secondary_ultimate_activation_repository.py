from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .eso_markup import normalize_eso_markup
from .skill_coefficient_repository import SkillCoefficientRepository


_SECONDARY_ULTIMATE_RE = re.compile(
    r"\bonce\s+summoned\s+you\s+can\s+activate\s+"
    r"(?P<activation>.+?)\s+for\s+"
    r"(?P<cost>\d+(?:\.\d+)?)\s+Ultimate\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SecondaryUltimateActivation:
    slotted_ability_name: str
    slotted_ability_id: int
    activation_name: str
    cost: float
    source: str = "ability.description"


@dataclass(frozen=True)
class SecondaryUltimateActivationResolution:
    activation: SecondaryUltimateActivation | None
    unresolved: tuple[str, ...] = ()


class SecondaryUltimateActivationRepository:
    """Resolve explicit secondary Ultimate activations from canonical ability text.

    This repository is intentionally narrow. It exists for persistent/summoned
    Ultimates whose slotted ability itself has no spend but whose canonical
    description explicitly names a repeat activation and its Ultimate cost.
    It does not guess costs from arbitrary numbers near the word "Ultimate".
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self.skill_repository = SkillCoefficientRepository(database_path)
        self._cache: dict[str, SecondaryUltimateActivationResolution] = {}

    def resolve_name(self, name: str) -> SecondaryUltimateActivationResolution:
        requested = str(name or "").strip()
        if not requested:
            return SecondaryUltimateActivationResolution(
                None,
                ("Ultimate ability name is required",),
            )

        cache_key = requested.casefold()
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        rank_resolution = self.skill_repository.resolve_name(requested)
        rank = rank_resolution.rank
        if rank is None:
            resolution = SecondaryUltimateActivationResolution(
                None,
                tuple(rank_resolution.unresolved) or (
                    f"Saved Ultimate not found: {requested}",
                ),
            )
            self._cache[cache_key] = resolution
            return resolution

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT ability_id, name, base_cost, base_mechanic, description
                FROM ability
                WHERE ability_id = ?
                """,
                (rank.ability_id,),
            ).fetchone()

        if row is None:
            resolution = SecondaryUltimateActivationResolution(
                None,
                (f"Ability row not found for resolved Ultimate ID {rank.ability_id}",),
            )
            self._cache[cache_key] = resolution
            return resolution

        base_cost = float(row["base_cost"] or 0.0)
        base_mechanic = int(row["base_mechanic"] or 0)
        if base_cost > 0:
            resolution = SecondaryUltimateActivationResolution(
                None,
                (
                    f"{rank.name} has a positive canonical base cost and does not require secondary-activation cost resolution",
                ),
            )
            self._cache[cache_key] = resolution
            return resolution

        if not (base_mechanic & 8):
            resolution = SecondaryUltimateActivationResolution(
                None,
                (
                    f"{rank.name} does not carry the canonical Ultimate resource mechanic",
                ),
            )
            self._cache[cache_key] = resolution
            return resolution

        description = normalize_eso_markup(str(row["description"] or "")).text
        match = _SECONDARY_ULTIMATE_RE.search(description)
        if match is None:
            resolution = SecondaryUltimateActivationResolution(
                None,
                (
                    f"{rank.name} has zero canonical base cost and no explicit secondary Ultimate activation cost in ability.description",
                ),
            )
            self._cache[cache_key] = resolution
            return resolution

        activation_name = " ".join(match.group("activation").split()).strip()
        cost = float(match.group("cost"))
        if not activation_name or cost <= 0:
            resolution = SecondaryUltimateActivationResolution(
                None,
                (
                    f"{rank.name} secondary Ultimate activation evidence is incomplete",
                ),
            )
            self._cache[cache_key] = resolution
            return resolution

        resolution = SecondaryUltimateActivationResolution(
            SecondaryUltimateActivation(
                slotted_ability_name=rank.name,
                slotted_ability_id=rank.ability_id,
                activation_name=activation_name,
                cost=cost,
            )
        )
        self._cache[cache_key] = resolution
        return resolution
