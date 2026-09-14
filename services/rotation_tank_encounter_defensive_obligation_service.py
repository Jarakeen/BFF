from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationActionKind
from services.encounter_evidence import ReconciledEncounterFact
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)


_TANK_TARGETS = frozenset(
    {
        "tank",
        "main tank",
        "off tank",
        "taunt target",
    }
)


@dataclass(frozen=True)
class RotationTankEncounterDefensiveWindowBinding:
    """Clock placement for one already-reviewed encounter mechanic occurrence.

    Encounter evidence owns what responses are supported and who they apply to.
    This binding owns only which reviewed fact is being scheduled, the identity of
    this occurrence, and where it lands on the rotation timeline. It does not
    reinterpret mechanic prose or manufacture timing from encounter descriptions.
    """

    occurrence_id: str
    fact_type: str
    fact_key: str
    window_start_seconds: float
    window_end_seconds: float
    minimum_responses: int = 1
    bar: str | None = None

    def __post_init__(self) -> None:
        occurrence_id = str(self.occurrence_id or "").strip()
        fact_type = str(self.fact_type or "").strip().casefold()
        fact_key = str(self.fact_key or "").strip().casefold()
        if not occurrence_id:
            raise ValueError("tank encounter defensive binding occurrence_id is required")
        if not fact_type:
            raise ValueError("tank encounter defensive binding fact_type is required")
        if not fact_key:
            raise ValueError("tank encounter defensive binding fact_key is required")
        object.__setattr__(self, "occurrence_id", occurrence_id)
        object.__setattr__(self, "fact_type", fact_type)
        object.__setattr__(self, "fact_key", fact_key)

        start = float(self.window_start_seconds)
        end = float(self.window_end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("tank encounter defensive binding start must be finite and non-negative")
        if not math.isfinite(end) or end < start:
            raise ValueError("tank encounter defensive binding end must be finite and >= start")
        object.__setattr__(self, "window_start_seconds", start)
        object.__setattr__(self, "window_end_seconds", end)

        minimum = int(self.minimum_responses)
        if minimum < 1:
            raise ValueError("tank encounter defensive binding minimum_responses must be positive")
        object.__setattr__(self, "minimum_responses", minimum)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank encounter defensive binding bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationTankEncounterDefensiveProjection:
    obligation: RotationTankDefensiveObligation | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.obligation is not None and not self.unresolved


class RotationTankEncounterDefensiveObligationService:
    """Project structured reviewed encounter evidence into tank obligations.

    Only explicit structured fields may prove block/dodge response semantics and
    tank applicability. Free-form prose remains presentation/research evidence until
    separately reviewed into structured facts. Timing remains caller-bound because
    many encounter facts prove mechanic behavior without proving an exact clock
    occurrence.
    """

    @staticmethod
    def project(
        *,
        fact: ReconciledEncounterFact,
        binding: RotationTankEncounterDefensiveWindowBinding,
    ) -> RotationTankEncounterDefensiveProjection:
        fact_type = str(fact.fact_type or "").strip().casefold()
        fact_key = str(fact.fact_key or "").strip().casefold()
        if fact_type != binding.fact_type or fact_key != binding.fact_key:
            return RotationTankEncounterDefensiveProjection(
                obligation=None,
                unresolved=(
                    "tank defensive encounter binding does not match reviewed fact identity",
                ),
            )

        if not fact.safe_for_review:
            return RotationTankEncounterDefensiveProjection(
                obligation=None,
                unresolved=(
                    f"{fact.fact_key}: encounter defensive evidence is conflicting",
                ),
            )

        value = fact.value
        if not isinstance(value, dict):
            return RotationTankEncounterDefensiveProjection(
                obligation=None,
                unresolved=(
                    f"{fact.fact_key}: encounter defensive evidence is not structured",
                ),
            )

        if not _explicit_tank_applicability(value):
            return RotationTankEncounterDefensiveProjection(
                obligation=None,
                unresolved=(
                    f"{fact.fact_key}: structured encounter evidence does not explicitly apply the response to a tank",
                ),
            )

        allowed = _explicit_defensive_actions(value)
        if not allowed:
            return RotationTankEncounterDefensiveProjection(
                obligation=None,
                unresolved=(
                    f"{fact.fact_key}: structured encounter evidence does not explicitly permit block or dodge",
                ),
            )

        provenance = tuple(
            dict.fromkeys(
                item
                for evidence in fact.evidence
                for item in (
                    str(evidence.source_name or "").strip(),
                    str(evidence.source_locator or "").strip(),
                )
                if item
            )
        )
        obligation_id = (
            f"{fact.encounter_id}:{fact_type}:{fact_key}:{binding.occurrence_id}"
        )
        return RotationTankEncounterDefensiveProjection(
            obligation=RotationTankDefensiveObligation(
                obligation_id=obligation_id,
                window_start_seconds=binding.window_start_seconds,
                window_end_seconds=binding.window_end_seconds,
                allowed_actions=allowed,
                minimum_responses=binding.minimum_responses,
                bar=binding.bar,
                provenance=provenance,
            )
        )


def _normalize_token(value: object) -> str:
    return str(value or "").strip().casefold().replace("_", " ").replace("-", " ")


def _explicit_tank_applicability(value: dict) -> bool:
    """Accept only structured fields that explicitly include a tank recipient."""

    if value.get("targets_every_player") is True:
        return True

    scalar_fields = (
        "target",
        "target_role",
        "tracking_target",
        "veteran_tracking_target",
        "hardmode_additional_tracking_target",
    )
    for field in scalar_fields:
        if _normalize_token(value.get(field)) in _TANK_TARGETS:
            return True

    for field in ("targets", "target_roles", "tracking_targets"):
        raw_values = value.get(field)
        if not isinstance(raw_values, (list, tuple)):
            continue
        if any(_normalize_token(item) in _TANK_TARGETS for item in raw_values):
            return True

    return False


def _explicit_defensive_actions(value: dict) -> tuple[RotationActionKind, ...]:
    """Read only explicit structured defensive response fields."""

    actions: list[RotationActionKind] = []

    responses = value.get("responses")
    if isinstance(responses, (list, tuple)):
        for raw in responses:
            response = _normalize_token(raw)
            if response == "block" and RotationActionKind.BLOCK not in actions:
                actions.append(RotationActionKind.BLOCK)
            elif response in {"dodge", "roll dodge"} and RotationActionKind.DODGE not in actions:
                actions.append(RotationActionKind.DODGE)

    if value.get("blockable") is True and RotationActionKind.BLOCK not in actions:
        actions.append(RotationActionKind.BLOCK)
    if value.get("dodgeable") is True and RotationActionKind.DODGE not in actions:
        actions.append(RotationActionKind.DODGE)

    return tuple(actions)


__all__ = [
    "RotationTankEncounterDefensiveObligationService",
    "RotationTankEncounterDefensiveProjection",
    "RotationTankEncounterDefensiveWindowBinding",
]
