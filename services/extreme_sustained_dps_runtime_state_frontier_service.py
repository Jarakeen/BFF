from __future__ import annotations

"""Explicit finite runtime-state families for generated sustained-DPS search.

The runtime-state universe is not inferred here. A caller may provide a finite family
only when it can separately prove that family is the complete denominator for the
branch being searched. The service preserves omitted scope so local closure cannot be
mistaken for global runtime closure.
"""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeStateChoice:
    runtime_state_id: str
    snapshot: ExtremeRuntimeSnapshot
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    effects: tuple[EffectVariant, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
            ("evidence", self.evidence),
            ("unresolved", self.unresolved),
            ("effects", self.effects),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"runtime-state choice {label} must be a tuple")
        value = str(self.runtime_state_id or "").strip()
        if not value:
            raise ValueError("runtime-state choice requires runtime_state_id")
        object.__setattr__(self, "runtime_state_id", value)
        if any(not isinstance(effect, EffectVariant) for effect in self.effects):
            raise TypeError(
                "runtime-state effects must contain canonical EffectVariant records"
            )
        object.__setattr__(self, "effects", tuple(self.effects))
        object.__setattr__(
            self,
            "evidence",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.evidence
                    if str(item).strip()
                )
            ),
        )
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeStateFrontier:
    choices: tuple[ExtremeSustainedDPSRuntimeStateChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("choices", self.choices),
            ("evidence", self.evidence),
            ("unresolved", self.unresolved),
            ("omitted_scope", self.omitted_scope),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"runtime-state frontier {label} must be a tuple")
        if any(
            not isinstance(choice, ExtremeSustainedDPSRuntimeStateChoice)
            for choice in self.choices
        ):
            raise TypeError(
                "runtime-state frontier choices must contain canonical runtime-state choices"
            )
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int) or self.candidate_count < 0:
            raise ValueError(
                "runtime-state frontier candidate_count must be a non-negative integer"
            )
        if self.candidate_count != len(self.choices):
            raise ValueError(
                "runtime-state frontier candidate_count must equal retained choice count"
            )
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("runtime-state frontier denominator_proven must be boolean")

        evidence = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.evidence
                if str(item).strip()
            )
        )
        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.unresolved
                if str(item).strip()
            )
        )
        omitted_scope = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.omitted_scope
                if str(item).strip()
            )
        )
        if self.denominator_proven and (not self.choices or unresolved):
            raise ValueError(
                "runtime-state frontier denominator cannot be proven with no choices or unresolved evidence"
            )

        object.__setattr__(self, "choices", tuple(self.choices))
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "unresolved", unresolved)
        object.__setattr__(self, "omitted_scope", omitted_scope)


class ExtremeSustainedDPSRuntimeStateFrontierService:
    """Validate one externally closed finite runtime-state family."""

    @classmethod
    def build(
        cls,
        choices: tuple[ExtremeSustainedDPSRuntimeStateChoice, ...],
        *,
        denominator_proven: bool,
        source: str,
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSRuntimeStateFrontier:
        if not isinstance(choices, tuple):
            raise TypeError("runtime-state choices must be a tuple")
        if any(not isinstance(choice, ExtremeSustainedDPSRuntimeStateChoice) for choice in choices):
            raise TypeError("runtime-state choices must contain canonical runtime-state choices")
        if not isinstance(denominator_proven, bool):
            raise TypeError("runtime-state denominator proof flag must be boolean")
        if not isinstance(omitted_scope, tuple):
            raise TypeError("runtime-state omitted scope must be a tuple")
        unresolved: list[str] = []
        seen: set[str] = set()
        rows: list[ExtremeSustainedDPSRuntimeStateChoice] = []

        for choice in choices:
            key = choice.runtime_state_id
            if key in seen:
                unresolved.append(f"Duplicate runtime-state identity: {key}")
                continue
            seen.add(key)
            rows.append(choice)
            unresolved.extend(
                f"{key}: {item}"
                for item in choice.unresolved
            )

        if not rows:
            unresolved.append("Finite runtime-state family is empty")
        if not denominator_proven:
            unresolved.append(
                "Finite runtime-state denominator is not externally proven complete"
            )

        deduped = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        omitted = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in omitted_scope
                if str(item).strip()
            )
        )
        complete = bool(rows) and denominator_proven and not deduped

        return ExtremeSustainedDPSRuntimeStateFrontier(
            choices=tuple(rows),
            candidate_count=len(rows),
            denominator_proven=complete,
            evidence=(
                f"Finite runtime-state choices retained: {len(rows)}",
                f"Runtime-state denominator source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Canonical runtime_state axis denominator is locally proven"
                    if complete
                    else "Canonical runtime_state axis denominator remains open"
                ),
                "This service validates supplied runtime states; it does not invent proc/cooldown/condition timelines",
            ),
            unresolved=deduped,
            omitted_scope=omitted,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeStateChoice",
    "ExtremeSustainedDPSRuntimeStateFrontier",
    "ExtremeSustainedDPSRuntimeStateFrontierService",
]
