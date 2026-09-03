from __future__ import annotations

import re

from models.build_model import ARMOR_SLOTS, PlayerBuild

from .build_candidate import BuildCandidate, BuildChange


# Only traits already resolved by the authoritative static build stack belong in
# the Phase 12 bounded search. Traits with known runtime/non-combat gaps stay out
# of candidate generation rather than becoming knowingly UNKNOWN candidates.
MODELED_ARMOR_TRAITS: tuple[str, ...] = (
    "Divines",
    "Infused",
    "Invigorating",
    "Reinforced",
    "Nirnhoned",
    "Impenetrable",
)


def enumerate_armor_trait_candidates(
    *,
    baseline_build: PlayerBuild,
    character_id: str,
    baseline_build_id: str,
    candidate_source: str = "phase12:armor-trait",
) -> tuple[BuildCandidate, ...]:
    """Enumerate deterministic one-slot armor-trait candidates.

    Only equipped armor slots are considered and every candidate changes exactly
    one ``Armor.<slot>.Trait`` field. The baseline build is cloned for each
    candidate and never mutated. Candidate generation does not rank traits or
    assume a healer-specific preferred trait.
    """

    candidates: list[BuildCandidate] = []
    for slot_name in ARMOR_SLOTS:
        entry = baseline_build.Armor.get(slot_name, {})
        if not _armor_equipped(entry):
            continue
        current = str(entry.get("Trait", "") or "").strip()

        for trait in MODELED_ARMOR_TRAITS:
            if trait.casefold() == current.casefold():
                continue

            candidate_build = PlayerBuild.from_dict(baseline_build.to_dict())
            candidate_build.Armor[slot_name]["Trait"] = trait
            candidates.append(
                BuildCandidate.from_build(
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    candidate_id=(
                        f"{baseline_build_id}:armor-trait:"
                        f"{_candidate_token(slot_name)}:{_candidate_token(trait)}"
                    ),
                    candidate_build=candidate_build,
                    changes=(
                        BuildChange.from_values(
                            path=f"Armor.{slot_name}.Trait",
                            before=current,
                            after=trait,
                            source=candidate_source,
                        ),
                    ),
                    candidate_source=candidate_source,
                )
            )

    return tuple(candidates)


def _armor_equipped(entry: dict[str, str]) -> bool:
    return bool(
        str(entry.get("Set", "") or "").strip()
        or str(entry.get("Set2", "") or "").strip()
        or str(entry.get("Weight", "") or "").strip()
    )


def _candidate_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")
    if not token:
        raise ValueError("Armor-trait candidate value cannot produce an empty candidate id.")
    return token
