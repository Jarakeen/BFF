from __future__ import annotations

"""Discover Ultimate-generation candidates from a saved reference snapshot.

This is a source-denominator service, not canonical combat math. It preserves the
reference's displayed rates and classifies which identities deserve later exact
tooltip, timing, targeting, and build-legality review.
"""

from dataclasses import dataclass
from enum import Enum
from html import unescape
import re


class UltimateSourceRouteStatus(str, Enum):
    MODELED = "modeled"
    ROUTE_INCOMPATIBLE = "route_incompatible"
    SEARCH_STATE_MUTATION = "search_state_mutation"
    EXACT_REVIEW_REQUIRED = "exact_review_required"


@dataclass(frozen=True)
class UltimateSourceReference:
    source_id: str
    label: str
    category: str
    displayed_rate: str | None
    route_status: UltimateSourceRouteStatus
    reason: str


class UltimateSourceReferenceFrontierService:
    _MODELED = frozenset({"light_attack", "minor_heroism", "major_heroism"})
    _ROUTE_INCOMPATIBLE = frozenset(
        {
            "erudites_rigor", "devout_guardian", "bastion_light",
            "malevolent_promise", "implacable_outcome", "savage_beast",
            "prism", "corpse_consumption", "transfer", "catalyst",
            "stalwart", "necrotic_potency",
        }
    )
    _SEARCH_MUTATIONS = frozenset(
        {
            "exhilarating_drain", "bloodspawn", "baron_zaudrus",
            "hide_of_the_werewolf", "arkasis", "pillagers_profit",
            "arkays_charity", "cryptcanon_vestments", "decisive",
        }
    )

    @staticmethod
    def _plain(value: str) -> str:
        return " ".join(unescape(re.sub(r"<[^>]+>", "", value)).split())

    @classmethod
    def _status(cls, source_id: str) -> tuple[UltimateSourceRouteStatus, str]:
        if source_id in cls._MODELED:
            return UltimateSourceRouteStatus.MODELED, (
                "Already represented by canonical base/Heroism generation events."
            )
        if source_id in cls._ROUTE_INCOMPATIBLE:
            return UltimateSourceRouteStatus.ROUTE_INCOMPATIBLE, (
                "Class, Class Mastery, or race identity conflicts with the "
                "Khajiit pure-Dragonknight Booming Voice route."
            )
        if source_id in cls._SEARCH_MUTATIONS:
            return UltimateSourceRouteStatus.SEARCH_STATE_MUTATION, (
                "Requires a separate skill, Vampire, weapon-trait, or named-gear search state."
            )
        return UltimateSourceRouteStatus.EXACT_REVIEW_REQUIRED, (
            "Exact canonical tooltip, cadence, self-targeting, and route legality require review."
        )

    @classmethod
    def parse(cls, document: str) -> tuple[UltimateSourceReference, ...]:
        text = str(document or "")
        sections = tuple(
            (match.start(), cls._plain(match.group(1)))
            for match in re.finditer(
                r'class="uc-section-title">([^<]+)</span>', text, flags=re.IGNORECASE
            )
        )
        matches = tuple(re.finditer(r'data-source="([^"]+)"', text))
        rows: list[tuple[str, str, str, str | None]] = []
        for index, match in enumerate(matches):
            source_id = match.group(1).strip()
            if not source_id:
                continue
            category = next(
                (label for position, label in reversed(sections) if position < match.start()),
                "Unclassified",
            )
            end = matches[index + 1].start() if index + 1 < len(matches) else match.start() + 4000
            fragment = text[match.start():min(len(text), end)]
            label_match = re.search(
                r'hx-tip-trigger__label">([^<]+)</span>', fragment, flags=re.IGNORECASE
            )
            label = cls._plain(label_match.group(1)) if label_match else source_id
            value_match = re.search(
                r'<span class="uc-val"[^>]*>([\s\S]*?)</span>\s*</div>',
                fragment,
                flags=re.IGNORECASE,
            )
            displayed_rate = cls._plain(value_match.group(1)) if value_match else None
            rows.append((source_id, label, category, displayed_rate))

        for match in re.finditer(
            r'data-class-source="([^"]+)"[\s\S]{0,700}?'
            r'hx-tip-trigger__label">([^<]+)</span>',
            text,
            flags=re.IGNORECASE,
        ):
            source_id = match.group(1).strip()
            if source_id:
                rows.append((source_id, cls._plain(match.group(2)), "Class Passive", None))

        if 'id="uc-decisive"' in text:
            rows.append(("decisive", "Decisive", "Weapon Trait", None))

        result: list[UltimateSourceReference] = []
        seen: set[str] = set()
        for source_id, label, category, displayed_rate in rows:
            if source_id in seen:
                continue
            seen.add(source_id)
            status, reason = cls._status(source_id)
            result.append(
                UltimateSourceReference(
                    source_id, label, category, displayed_rate, status, reason
                )
            )
        return tuple(result)


__all__ = [
    "UltimateSourceReference",
    "UltimateSourceReferenceFrontierService",
    "UltimateSourceRouteStatus",
]
