from __future__ import annotations

"""Classify unresolved recovery-set mechanics into proof-owned semantic branches.

This layer owns classification only. It does not score a character sheet and does
not infer that a runtime condition is active. The purpose is to turn the small set
of recovery-relevant, mechanic-unmapped descriptions into explicit search branches
or explicit non-challengers without relying on a set-name allowlist.
"""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.eso_markup import normalize_eso_markup


class ExtremeRecoverySpecialBranchKind(str, Enum):
    CONDITIONAL_FLAT = "conditional_flat"
    STACKED_FLAT = "stacked_flat"
    CONDITIONAL_PERCENT = "conditional_percent"
    FORMULA = "formula"
    NAMED_BUFF = "named_buff"
    NEGATIVE_ONLY = "negative_only"
    SELF_INELIGIBLE = "self_ineligible"
    SEARCH_STATE_MUTATION = "search_state_mutation"


@dataclass(frozen=True)
class ExtremeRecoverySpecialBranch:
    set_name: str
    piece_count: int
    kind: ExtremeRecoverySpecialBranchKind
    can_raise_self: bool
    flat_ceiling: float | None = None
    percent_ceiling: float | None = None
    condition: str | None = None
    search_state_rule: str | None = None
    description: str = ""


@dataclass(frozen=True)
class ExtremeRecoverySpecialBranchCatalog:
    branches: tuple[ExtremeRecoverySpecialBranch, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_classified(self) -> bool:
        return bool(self.branches) and not self.unresolved

    @property
    def positive_challengers(self) -> tuple[ExtremeRecoverySpecialBranch, ...]:
        return tuple(row for row in self.branches if row.can_raise_self)

    @property
    def reviewed_non_challengers(self) -> tuple[ExtremeRecoverySpecialBranch, ...]:
        return tuple(row for row in self.branches if not row.can_raise_self)


class ExtremeGearSetRecoverySpecialBranchService:
    """Description-driven recovery special classification with fail-closed fallback."""

    _SEARCH_STATE_PHRASES = (
        ("two mundus stone boons", "allows_two_mundus"),
        ("disable all other item set bonuses", "suppresses_other_set_bonuses"),
        ("unable to swap between your primary and backup weapon sets", "one_bar_only"),
    )

    @staticmethod
    def _text(description: str) -> str:
        return " ".join(normalize_eso_markup(str(description or "")).text.casefold().split())

    @staticmethod
    def _shared_recovery_pattern() -> str:
        # ESO tooltips use several list orders, for example
        # "Health, Magicka, and Stamina Recovery" and
        # "Stamina, Magicka, and Health Recovery". Match the three-resource list
        # without assigning semantic meaning to the order.
        resource = r"(?:health|magicka|stamina)"
        return rf"{resource},?\s+{resource},?\s+(?:and\s+)?{resource}\s+recovery"

    @classmethod
    def _has_shared_recovery(cls, text: str, resource: str) -> bool:
        match = re.search(cls._shared_recovery_pattern(), text)
        if match is None:
            return False
        phrase = match.group(0)
        return all(name in phrase for name in ("health", "magicka", "stamina")) and resource in phrase

    @classmethod
    def _recovery_clause(cls, text: str, resource: str) -> str:
        """Return the smallest sentence-like clause that owns target recovery text."""
        candidates = re.split(r"(?<=[.;])\s+|\n+", text)
        target = f"{resource} recovery"
        for clause in candidates:
            if target in clause or cls._has_shared_recovery(clause, resource):
                return clause
        return text

    @classmethod
    def _flat_ceiling(cls, text: str, resource: str) -> float | None:
        clause = cls._recovery_clause(text, resource)
        target = re.escape(f"{resource} recovery")
        shared = cls._shared_recovery_pattern()

        # Amount before the stat: "gain 35-1505 Health Recovery" / "adds 1011 Health Recovery".
        before = re.search(
            rf"(?:gain|adds?|receive)\s+(?:\d+(?:\.\d+)?-)?(?P<value>\d+(?:\.\d+)?)\s+"
            rf"(?:{target}|{shared})\b",
            clause,
        )
        if before:
            return float(before.group("value"))

        # Parallel reward clauses: "gain 7-341 Weapon and Spell Damage and 7-341 Health Recovery".
        parallel = re.search(
            rf"\band\s+(?:\d+(?:\.\d+)?-)?(?P<value>\d+(?:\.\d+)?)\s+(?:{target}|{shared})\b",
            clause,
        )
        if parallel:
            return float(parallel.group("value"))

        # Amount after the stat: "Health Recovery by 8-356" / "increased by 18-800".
        after = re.search(
            rf"(?:{target}|{shared})\b[^.;]{{0,45}}?\b(?:by|of)\s+"
            rf"(?:\d+(?:\.\d+)?-)?(?P<value>\d+(?:\.\d+)?)\b",
            clause,
        )
        if after:
            return float(after.group("value"))

        # Shared fixed amount often appears before the list: "gain 465 Health, Magicka, and Stamina Recovery".
        shared_before = re.search(
            rf"(?:gain|adds?|receive)\s+(?P<value>\d+(?:\.\d+)?)\s+{shared}\b",
            clause,
        )
        return float(shared_before.group("value")) if shared_before else None

    @classmethod
    def classify(
        cls,
        *,
        set_name: str,
        piece_count: int,
        description: str,
        objective_key: str = "health_recovery",
    ) -> ExtremeRecoverySpecialBranch | None:
        key = str(objective_key or "").strip().casefold()
        if key not in {"health_recovery", "magicka_recovery", "stamina_recovery"}:
            raise KeyError(f"unreviewed recovery objective: {objective_key!r}")

        resource = {
            "health_recovery": "health",
            "magicka_recovery": "magicka",
            "stamina_recovery": "stamina",
        }[key]
        text = cls._text(description)
        if not text:
            return None

        for phrase, rule in cls._SEARCH_STATE_PHRASES:
            if phrase in text:
                can_raise = False
                percent = None
                named = None
                if rule == "one_bar_only":
                    named = {
                        "health": "minor fortitude",
                        "magicka": "minor intellect",
                        "stamina": "minor endurance",
                    }[resource]
                    can_raise = named in text
                    percent = 15.0 if can_raise else None
                return ExtremeRecoverySpecialBranch(
                    set_name=set_name,
                    piece_count=int(piece_count),
                    kind=ExtremeRecoverySpecialBranchKind.SEARCH_STATE_MUTATION,
                    can_raise_self=can_raise,
                    percent_ceiling=percent,
                    condition=named.replace(" ", "_") if named and can_raise else None,
                    search_state_rule=rule,
                    description=description,
                )

        if "cannot affect yourself" in text or "cannot affect self" in text:
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.SELF_INELIGIBLE,
                can_raise_self=False,
                description=description,
            )

        target_phrase = f"{resource} recovery"
        shared_recovery = cls._has_shared_recovery(text, resource)
        relevant = target_phrase in text or shared_recovery
        named_buff = {
            "health": ("major fortitude", "minor fortitude"),
            "magicka": ("major intellect", "minor intellect"),
            "stamina": ("major endurance", "minor endurance"),
        }[resource]

        for phrase in named_buff:
            if phrase in text:
                percent = 30.0 if phrase.startswith("major") else 15.0
                return ExtremeRecoverySpecialBranch(
                    set_name=set_name,
                    piece_count=int(piece_count),
                    kind=ExtremeRecoverySpecialBranchKind.NAMED_BUFF,
                    can_raise_self=True,
                    percent_ceiling=percent,
                    condition=phrase.replace(" ", "_") if phrase else None,
                    description=description,
                )

        if not relevant:
            return None

        target_pattern = re.escape(target_phrase)
        shared_pattern = cls._shared_recovery_pattern()
        negative_recovery = re.search(
            rf"\b(?:reduce|reduces|reduced|reducing|lower|lowers|lowered|lowering)\b"
            rf"[^.;]{{0,140}}?(?:{target_pattern}|{shared_pattern})\b[^.;]{{0,35}}?\bby\s+\d+(?:\.\d+)?%?",
            text,
        ) or re.search(
            rf"(?:{target_pattern}|{shared_pattern})\b[^.;]{{0,50}}?\b(?:reduced|lowered)\b[^.;]{{0,25}}?\bby\s+\d+(?:\.\d+)?%?",
            text,
        )
        negative_markers = (
            "lowers the health recovery",
            "reducing their health recovery",
            "health recovery are reduced",
            "health recovery is reduced",
            "health recovery reduced by",
            "reduce your health, magicka, and stamina recovery",
        )
        if negative_recovery or any(marker in text for marker in negative_markers):
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.NEGATIVE_ONLY,
                can_raise_self=False,
                description=description,
            )

        if "sum total physical resistance and spell resistance" in text:
            cap_match = re.search(r"maximum of\s+(\d+(?:\.\d+)?)", text)
            ceiling = float(cap_match.group(1)) if cap_match else None
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.FORMULA,
                can_raise_self=True,
                flat_ceiling=ceiling,
                condition="resistance_scaled",
                description=description,
            )

        percent_match = re.search(
            r"(?:increase(?:s|d)?|increasing)\s+(?:your\s+)?(?:"
            + shared_pattern
            + "|"
            + re.escape(target_phrase)
            + r")\s+by\s+(\d+(?:\.\d+)?)%",
            text,
        )
        if percent_match:
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.CONDITIONAL_PERCENT,
                can_raise_self=True,
                percent_ceiling=float(percent_match.group(1)),
                description=description,
            )

        if "stack" in text and relevant:
            up_to = re.search(r"recovery[^.]{0,100}?up to\s+(\d+(?:\.\d+)?)", text)
            ceiling = float(up_to.group(1)) if up_to else None
            if ceiling is None:
                counts = [
                    int(v)
                    for v in re.findall(r"up to\s+(\d+)\s+(?:stacks(?:\s+max)?|times)", text)
                ]
                per_stack_after = re.search(
                    rf"(?:each stack[^.]*?|(?:{target_pattern}|{shared_pattern})[^.]*?)"
                    rf"(?:{target_pattern}|{shared_pattern})?[^.]*?\bby\s+"
                    rf"(?P<value>\d+(?:\.\d+)?)\s+per stack\b",
                    text,
                )
                per_stack_before = re.search(
                    rf"each stack[^.]*?\b(?:grants?|adds?|increases?)\s+"
                    rf"(?P<value>\d+(?:\.\d+)?)\s+(?:{target_pattern}|{shared_pattern})\b",
                    text,
                )
                per_stack_legacy = re.search(
                    rf"each stack[^.]*?(?:{target_pattern}|{shared_pattern})[^.]*?\bby\s+"
                    rf"(?P<value>\d+(?:\.\d+)?)\b",
                    text,
                )
                per_stack = per_stack_after or per_stack_before or per_stack_legacy
                if counts and per_stack:
                    ceiling = max(counts) * float(per_stack.group("value"))
            if ceiling is not None:
                return ExtremeRecoverySpecialBranch(
                    set_name=set_name,
                    piece_count=int(piece_count),
                    kind=ExtremeRecoverySpecialBranchKind.STACKED_FLAT,
                    can_raise_self=True,
                    flat_ceiling=ceiling,
                    condition="max_stacks",
                    description=description,
                )

        flat = cls._flat_ceiling(text, resource)
        if flat is not None:
            return ExtremeRecoverySpecialBranch(
                set_name=set_name,
                piece_count=int(piece_count),
                kind=ExtremeRecoverySpecialBranchKind.CONDITIONAL_FLAT,
                can_raise_self=True,
                flat_ceiling=flat,
                condition="runtime_condition_required",
                description=description,
            )

        return None

    @classmethod
    def build(cls, rows, *, objective_key: str = "health_recovery") -> ExtremeRecoverySpecialBranchCatalog:
        branches: list[ExtremeRecoverySpecialBranch] = []
        unresolved: list[str] = []
        for set_name, piece_count, description in rows:
            branch = cls.classify(
                set_name=str(set_name),
                piece_count=int(piece_count),
                description=str(description),
                objective_key=objective_key,
            )
            if branch is None:
                unresolved.append(f"{set_name} ({piece_count}): unclassified recovery mechanic")
            else:
                branches.append(branch)
        return ExtremeRecoverySpecialBranchCatalog(
            branches=tuple(sorted(branches, key=lambda row: (row.set_name.casefold(), row.piece_count))),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeGearSetRecoverySpecialBranchService",
    "ExtremeRecoverySpecialBranch",
    "ExtremeRecoverySpecialBranchCatalog",
    "ExtremeRecoverySpecialBranchKind",
]
