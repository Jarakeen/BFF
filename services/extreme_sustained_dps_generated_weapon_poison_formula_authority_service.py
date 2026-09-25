from __future__ import annotations

"""Resolve exact generated front/back weapon-poison formula provenance.

Generated Objective #32 poison search selects canonical AlchemyFormula objects, then
flattens their canonical IDs into PlayerBuild front/back poison fields so existing
runtime activation logic can see that a poison is equipped. This service preserves the
stronger provenance object and verifies that the flattened build still agrees with the
selected formula loadout before downstream poison consequence authority uses it.
"""

from dataclasses import dataclass

from minmax.alchemy_formula_catalog import AlchemyFormula


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry:
    bar: str
    poison_id: str
    formula: AlchemyFormula


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority:
    entries: tuple[ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    def formula_for(self, poison_id: str) -> AlchemyFormula | None:
        key = str(poison_id or "").strip().casefold()
        matches = tuple(
            entry.formula
            for entry in self.entries
            if entry.poison_id.strip().casefold() == key
        )
        if len(matches) != 1:
            return None
        return matches[0]


class ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService:
    """Validate generated poison loadout provenance against the assembled build."""

    @staticmethod
    def _selected_poison(build, bar: str) -> str:
        field = "FrontBarPoison" if bar == "front" else "BackBarPoison"
        return str(getattr(build, field, "") or "").strip()

    @classmethod
    def resolve(
        cls,
        state: object,
    ) -> ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority:
        late = getattr(state, "late", None)
        assembled = getattr(late, "assembled", None)
        poison_loadout = (
            None if assembled is None else getattr(assembled, "poison_loadout", None)
        )
        if poison_loadout is None:
            poison_loadout = getattr(late, "poison_loadout", None)

        if assembled is None:
            return ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
                entries=(),
                unresolved=(
                    "generated poison formula authority requires assembled candidate state",
                ),
            )
        build = getattr(assembled, "build", None)
        if build is None:
            return ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
                entries=(),
                unresolved=(
                    "generated poison formula authority requires assembled PlayerBuild",
                ),
            )

        front_flat = cls._selected_poison(build, "front")
        back_flat = cls._selected_poison(build, "back")
        if poison_loadout is None:
            if front_flat or back_flat:
                return ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
                    entries=(),
                    unresolved=(
                        "assembled build carries generated poison identity without retained poison-loadout provenance",
                    ),
                )
            return ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
                entries=(),
                evidence=("Generated candidate carries no weapon poison on either bar.",),
            )

        entries: list[ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry] = []
        unresolved: list[str] = []

        for bar in ("front", "back"):
            selection = getattr(poison_loadout, bar, None)
            selected_label = str(
                getattr(selection, "selected_label", "") or ""
            ).strip()
            formula = getattr(selection, "formula", None)
            flattened = cls._selected_poison(build, bar)

            if selected_label != flattened:
                unresolved.append(
                    f"{bar} generated poison identity mismatch: loadout={selected_label or '(none)'} "
                    f"assembled_build={flattened or '(none)'}"
                )

            if not selected_label:
                if formula is not None:
                    unresolved.append(
                        f"{bar} no-poison selection unexpectedly retains formula provenance"
                    )
                continue

            if not isinstance(formula, AlchemyFormula):
                unresolved.append(
                    f"{bar} generated poison {selected_label} has no canonical AlchemyFormula provenance"
                )
                continue

            formula_id = str(formula.canonical_id or "").strip()
            if not formula_id:
                unresolved.append(
                    f"{bar} generated poison formula has no canonical identity"
                )
                continue
            if selected_label != formula_id:
                unresolved.append(
                    f"{bar} generated poison identity does not match formula canonical ID: "
                    f"{selected_label} != {formula_id}"
                )
                continue

            entries.append(
                ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry(
                    bar=bar,
                    poison_id=selected_label,
                    formula=formula,
                )
            )

        deduped_unresolved = tuple(
            dict.fromkeys(row for row in unresolved if str(row).strip())
        )
        return ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
            entries=tuple(entries),
            evidence=(
                f"Generated poison formulas retained: {len(entries)}",
                f"Generated front poison identity: {front_flat or '(none)'}",
                f"Generated back poison identity: {back_flat or '(none)'}",
                "Generated poison formula identity is validated against the assembled build before downstream consequence resolution.",
            ),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority",
    "ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService",
    "ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry",
]
