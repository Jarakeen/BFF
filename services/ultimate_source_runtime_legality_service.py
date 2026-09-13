from __future__ import annotations

"""Exact runtime/recipient review for Ultimate sources on the recovery route."""

from dataclasses import dataclass
from enum import Enum


class UltimateSourceRuntimeStatus(str, Enum):
    COMPATIBLE_INCREMENT = "compatible_increment"
    SELF_INCOMPATIBLE = "self_incompatible"
    ROUTE_INCOMPATIBLE = "route_incompatible"
    SEARCH_STATE_MUTATION = "search_state_mutation"
    CANONICAL_EVIDENCE_REQUIRED = "canonical_evidence_required"


@dataclass(frozen=True)
class UltimateSourceRuntimeReview:
    source_id: str
    status: UltimateSourceRuntimeStatus
    reason: str
    generated_ultimate_ceiling: float = 0.0
    remaining_ultimate_gap: float = 0.0


class UltimateSourceRuntimeLegalityService:
    """Apply reviewed canonical targeting and timing without scoring equipment."""

    _SEARCH_MUTATIONS = frozenset(
        {
            "exhilarating_drain",
            "bloodspawn",
            "baron_zaudrus",
            "hide_of_the_werewolf",
            "arkasis",
            "arkays_charity",
            "decisive",
        }
    )

    @staticmethod
    def _contains(records: tuple[str, ...], *fragments: str) -> bool:
        text = "\n".join(records).casefold()
        return all(fragment.casefold() in text for fragment in fragments)

    @classmethod
    def review(
        cls,
        source_id: str,
        *,
        canonical_records: tuple[str, ...] = (),
        required_additional_ultimate: float = 114.0,
        booming_voice_cast_seconds: float = 0.0,
        score_seconds: float = 24.999,
        trigger_seconds: tuple[float, ...] = (),
    ) -> UltimateSourceRuntimeReview:
        source_id = str(source_id or "").strip()
        gap = max(0.0, float(required_additional_ultimate))

        if source_id == "pillagers_profit":
            if not cls._contains(canonical_records, "other group members"):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical recipient clause is missing.",
                    remaining_ultimate_gap=gap,
                )
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.SELF_INCOMPATIBLE,
                "The set grants Ultimate to other group members, not the caster whose Strategic Reserve is scored.",
                remaining_ultimate_gap=gap,
            )

        if source_id == "cryptcanon_vestments":
            if not cls._contains(canonical_records, "can no longer cast ultimate abilities"):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical Ultimate-cast restriction is missing.",
                    remaining_ultimate_gap=gap,
                )
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.ROUTE_INCOMPATIBLE,
                "The mythic prevents the Ultimate cast required to start Booming Voice.",
                remaining_ultimate_gap=gap,
            )

        if source_id == "blessing_peak":
            if not cls._contains(
                canonical_records,
                "generate |cffffff1|r ultimate",
                "once every |cffffff6|r seconds",
            ):
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "The canonical amount and six-second cadence are missing.",
                    remaining_ultimate_gap=gap,
                )
            ordered = tuple(sorted(float(value) for value in trigger_seconds))
            legal_window = all(
                float(booming_voice_cast_seconds) < value <= float(score_seconds)
                for value in ordered
            )
            legal_cadence = all(
                later - earlier >= 6.0 - 1e-9
                for earlier, later in zip(ordered, ordered[1:])
            )
            if not ordered or not legal_window or not legal_cadence:
                return UltimateSourceRuntimeReview(
                    source_id,
                    UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
                    "A legal post-cast Earthen Heart trigger witness is required.",
                    remaining_ultimate_gap=gap,
                )
            generated = float(len(ordered))
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.COMPATIBLE_INCREMENT,
                "The pure Dragonknight route can trigger the passive at the supplied legal six-second cadence.",
                generated_ultimate_ceiling=generated,
                remaining_ultimate_gap=max(0.0, gap - generated),
            )

        if source_id in cls._SEARCH_MUTATIONS:
            return UltimateSourceRuntimeReview(
                source_id,
                UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
                "Exact runtime evidence is compatible with continued review, but the source changes skill, Vampire, gear, or weapon-trait state.",
                remaining_ultimate_gap=gap,
            )

        return UltimateSourceRuntimeReview(
            source_id,
            UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
            "No exact runtime-legality rule owns this source.",
            remaining_ultimate_gap=gap,
        )


__all__ = [
    "UltimateSourceRuntimeLegalityService",
    "UltimateSourceRuntimeReview",
    "UltimateSourceRuntimeStatus",
]
