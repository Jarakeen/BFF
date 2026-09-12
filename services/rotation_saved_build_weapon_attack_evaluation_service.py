from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.build_candidate_damage import calculation_result_from_build_context
from minmax.build_evaluation import BuildEvaluation
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.combat_contribution import CombatContribution
from models.build_model import PlayerBuild
from services.rotation_static_build_context_service import RotationStaticBuildContextResolution


@dataclass(frozen=True)
class RotationWeaponAttackBuildEvaluationResolution:
    """Canonical CharacterBuild plus bar-specific weapon-attack evaluations."""

    build: CharacterBuild | None
    evaluations: tuple[tuple[str, BuildEvaluation], ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.build is not None and bool(self.evaluations) and not self.unresolved

    def evaluation_for(self, bar: str) -> BuildEvaluation | None:
        key = str(bar or "").strip().casefold()
        for candidate_bar, evaluation in self.evaluations:
            if candidate_bar == key:
                return evaluation
        return None


class RotationSavedBuildWeaponAttackContributionService:
    """Resolve reviewed saved-build modifier buckets used by LA/HA formulas.

    The canonical weapon-attack calculators consume historical ``CombatContribution``
    buckets. This adapter maps only saved-build Champion Point facts whose semantics are
    explicit and reviewed. It does not infer uptime or synthesize unknown modifier
    families.
    """

    _WEAPONS_EXPERT_THRESHOLDS = (10, 20, 30, 40, 50)
    _WEAPONS_EXPERT_PER_STAGE = 0.04
    _MASTER_AT_ARMS_THRESHOLDS = (25, 50)
    _MASTER_AT_ARMS_PER_STAGE = 0.03
    _DEADLY_AIM_THRESHOLDS = (25, 50)
    _DEADLY_AIM_PER_STAGE = 0.03

    @staticmethod
    def _key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _points(value: object) -> int | None:
        try:
            points = int(str(value or "0").strip() or "0")
        except (TypeError, ValueError):
            return None
        return points if points >= 0 else None

    @staticmethod
    def _stages(points: int, thresholds: tuple[int, ...]) -> int:
        return sum(1 for threshold in thresholds if points >= threshold)

    @staticmethod
    def _contribution(source: str, effect_type: str, value: float) -> CombatContribution:
        return CombatContribution(
            source=source,
            effect_type=effect_type,
            raw_value=float(value),
            uptime=1.0,
            effective_value=float(value),
        )

    def resolve(
        self,
        build: PlayerBuild,
    ) -> tuple[tuple[CombatContribution, ...], tuple[str, ...]]:
        contributions: list[CombatContribution] = []
        unresolved: list[str] = []

        for entry in tuple(getattr(build, "ChampionPoints", ()) or ()):
            name = str(getattr(entry, "Name", "") or "").strip()
            if not name:
                continue
            key = self._key(name)
            if key not in {"weapons expert", "master-at-arms", "deadly aim"}:
                continue

            points = self._points(getattr(entry, "Points", ""))
            if points is None:
                unresolved.append(
                    f"Champion Point {name}: allocation is not a non-negative integer"
                )
                continue

            if key == "weapons expert":
                stages = self._stages(points, self._WEAPONS_EXPERT_THRESHOLDS)
                value = stages * self._WEAPONS_EXPERT_PER_STAGE
                if value:
                    source = f"Champion Point: Weapons Expert ({points} points)"
                    contributions.append(self._contribution(source, "cp_la_damage", value))
                    contributions.append(self._contribution(source, "cp_ha_damage", value))
                continue

            if key == "master-at-arms":
                stages = self._stages(points, self._MASTER_AT_ARMS_THRESHOLDS)
                value = stages * self._MASTER_AT_ARMS_PER_STAGE
                if value:
                    contributions.append(
                        self._contribution(
                            f"Champion Point: Master-at-Arms ({points} points)",
                            "direct_damage_done",
                            value,
                        )
                    )
                continue

            stages = self._stages(points, self._DEADLY_AIM_THRESHOLDS)
            value = stages * self._DEADLY_AIM_PER_STAGE
            if value:
                contributions.append(
                    self._contribution(
                        f"Champion Point: Deadly Aim ({points} points)",
                        "single_target_damage_done",
                        value,
                    )
                )

        return tuple(contributions), tuple(dict.fromkeys(unresolved))


class RotationSavedBuildWeaponAttackEvaluationService:
    """Bridge canonical saved-build static contexts into LA/HA evaluation evidence.

    Static stats remain owned by ``RotationStaticBuildContextService``. Canonical build
    structure remains owned by ``SavedBuildCharacterAdapter``. This service only packages
    those existing truths into the ``BuildEvaluation`` contract consumed by the reviewed
    light/heavy-attack calculators and adds explicitly mapped weapon-attack modifier
    contributions.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        build_adapter: SavedBuildCharacterAdapter | None = None,
        contribution_service: RotationSavedBuildWeaponAttackContributionService | None = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(self.database_path)
        self.contribution_service = (
            contribution_service or RotationSavedBuildWeaponAttackContributionService()
        )

    def resolve(
        self,
        *,
        player_build: PlayerBuild,
        static_context: RotationStaticBuildContextResolution,
    ) -> RotationWeaponAttackBuildEvaluationResolution:
        if not static_context.resolved:
            detail = tuple(static_context.unresolved) or (
                "canonical static build context is unresolved",
            )
            return RotationWeaponAttackBuildEvaluationResolution(
                build=None,
                unresolved=detail,
            )

        character_id = str(
            getattr(static_context.progression, "character_id", "") or ""
        ).strip() or None
        adaptation = self.build_adapter.adapt(
            player_build,
            character_id=character_id,
        )
        if adaptation.build is None or adaptation.unresolved:
            return RotationWeaponAttackBuildEvaluationResolution(
                build=adaptation.build,
                unresolved=tuple(adaptation.unresolved) or (
                    "canonical saved-build adaptation is unavailable",
                ),
            )

        contributions, contribution_unresolved = self.contribution_service.resolve(
            player_build
        )
        unresolved = list(contribution_unresolved)
        evaluations: list[tuple[str, BuildEvaluation]] = []

        for context in static_context.contexts:
            calculation = calculation_result_from_build_context(context)
            if calculation is None:
                unresolved.append(
                    f"{context.active_bar} weapon-attack evaluation requires resolved canonical core stats"
                )
                continue
            evaluations.append(
                (
                    context.active_bar,
                    BuildEvaluation(
                        stats=calculation,
                        combat_effects=(),
                        combat_contributions=contributions,
                    ),
                )
            )

        return RotationWeaponAttackBuildEvaluationResolution(
            build=adaptation.build,
            evaluations=tuple(evaluations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationSavedBuildWeaponAttackContributionService",
    "RotationSavedBuildWeaponAttackEvaluationService",
    "RotationWeaponAttackBuildEvaluationResolution",
]
