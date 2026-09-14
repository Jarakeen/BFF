from __future__ import annotations

"""Compose one fully-resolved Extreme Recovery record from proven flat and percent inputs.

This service owns arithmetic only. Discovery, legality, runtime conditions, and stochastic
proofs remain with their existing canonical owners. Callers therefore provide explicit
proof gates alongside already-resolved objective contributions instead of asking this
layer to reinterpret mechanics.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ExtremeRecoveryScoreComponent:
    name: str
    value: float


@dataclass(frozen=True)
class ExtremeRecoveryProofGate:
    name: str
    proven: bool
    detail: str = ""


@dataclass(frozen=True)
class ExtremeRecoveryFinalScore:
    objective_key: str
    base_value: float
    additive_components: tuple[ExtremeRecoveryScoreComponent, ...]
    percent_components: tuple[ExtremeRecoveryScoreComponent, ...]
    proof_gates: tuple[ExtremeRecoveryProofGate, ...]
    pre_percent_total: float
    total_percent: float
    final_value: float
    unresolved: tuple[str, ...] = ()

    @property
    def proof_complete(self) -> bool:
        return not self.unresolved and all(gate.proven for gate in self.proof_gates)


class ExtremeRecoveryFinalScoreService:
    """Apply the shared ESO recovery arithmetic to already-proven components."""

    @staticmethod
    def compose(
        *,
        objective_key: str,
        base_value: float,
        additive_components: tuple[ExtremeRecoveryScoreComponent, ...],
        percent_components: tuple[ExtremeRecoveryScoreComponent, ...],
        proof_gates: tuple[ExtremeRecoveryProofGate, ...] = (),
    ) -> ExtremeRecoveryFinalScore:
        objective = str(objective_key or "").strip().casefold()
        unresolved: list[str] = []
        if not objective.endswith("_recovery"):
            unresolved.append(f"unsupported recovery objective: {objective_key!r}")

        base = float(base_value)
        if not math.isfinite(base) or base < 0.0:
            unresolved.append(f"invalid base Recovery value: {base_value!r}")
            base = 0.0

        def validate(
            rows: tuple[ExtremeRecoveryScoreComponent, ...],
            *,
            kind: str,
        ) -> tuple[ExtremeRecoveryScoreComponent, ...]:
            seen: set[str] = set()
            valid: list[ExtremeRecoveryScoreComponent] = []
            for row in rows:
                name = str(row.name or "").strip()
                key = name.casefold()
                value = float(row.value)
                if not name:
                    unresolved.append(f"{kind} Recovery component has no name")
                    continue
                if key in seen:
                    unresolved.append(f"duplicate {kind} Recovery component: {name}")
                    continue
                seen.add(key)
                if not math.isfinite(value):
                    unresolved.append(f"{name}: non-finite {kind} Recovery value {row.value!r}")
                    continue
                valid.append(ExtremeRecoveryScoreComponent(name, value))
            return tuple(valid)

        additive = validate(additive_components, kind="additive")
        percent = validate(percent_components, kind="percent")
        pre_percent = base + sum(row.value for row in additive)
        total_percent = sum(row.value for row in percent)
        final = pre_percent * (1.0 + total_percent / 100.0)

        return ExtremeRecoveryFinalScore(
            objective_key=objective,
            base_value=base,
            additive_components=additive,
            percent_components=percent,
            proof_gates=tuple(proof_gates),
            pre_percent_total=pre_percent,
            total_percent=total_percent,
            final_value=final,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeRecoveryFinalScore",
    "ExtremeRecoveryFinalScoreService",
    "ExtremeRecoveryProofGate",
    "ExtremeRecoveryScoreComponent",
]
