from __future__ import annotations

import re

from models.build_model import ARMOR_SLOTS, PlayerBuild

from .build_candidate import BuildCandidate, BuildChange


# These are the armor enchant families already routed through the authoritative
# GearStatInputResolver -> ArmorGlyphEffectRepository path.
MODELED_ARMOR_ENCHANTS: tuple[str, ...] = (
    "Max Health",
    "Max Magicka",
    "Max Stamina",
    "Prismatic Defense",
)


def enumerate_armor_enchant_candidates(
    *,
    baseline_build: PlayerBuild,
    character_id: str,
    baseline_build_id: str,
    candidate_source: str = "phase12:armor-enchant",
) -> tuple[BuildCandidate, ...]:
    """Enumerate deterministic one-slot armor-enchant candidates.

    The existing armor glyph resolver only has verified max-level scaling for
    CP160 Truly Superb glyphs. Candidate generation therefore uses that same
    boundary rather than manufacturing UNKNOWN candidates from incomplete item
    metadata. Every candidate changes exactly one ``Armor.<slot>.Enchant`` field
    and leaves the saved baseline untouched.
    """

    candidates: list[BuildCandidate] = []
    for slot_name in ARMOR_SLOTS:
        entry = baseline_build.Armor.get(slot_name, {})
        if not _eligible_slot(entry):
            continue

        current = str(entry.get("Enchant", "") or "").strip()
        for enchant in MODELED_ARMOR_ENCHANTS:
            if enchant.casefold() == current.casefold():
                continue

            candidate_build = PlayerBuild.from_dict(baseline_build.to_dict())
            candidate_build.Armor[slot_name]["Enchant"] = enchant
            candidates.append(
                BuildCandidate.from_build(
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    candidate_id=(
                        f"{baseline_build_id}:armor-enchant:"
                        f"{_candidate_token(slot_name)}:{_candidate_token(enchant)}"
                    ),
                    candidate_build=candidate_build,
                    changes=(
                        BuildChange.from_values(
                            path=f"Armor.{slot_name}.Enchant",
                            before=current,
                            after=enchant,
                            source=candidate_source,
                        ),
                    ),
                    candidate_source=candidate_source,
                )
            )

    return tuple(candidates)


def _eligible_slot(entry: dict[str, str]) -> bool:
    equipped = bool(
        str(entry.get("Set", "") or "").strip()
        or str(entry.get("Set2", "") or "").strip()
        or str(entry.get("Weight", "") or "").strip()
    )
    if not equipped:
        return False
    return (
        str(entry.get("Level", "") or "").strip().casefold() == "cp160"
        and str(entry.get("EnchantTier", "") or "").strip().casefold() == "truly superb"
    )


def _candidate_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")
    if not token:
        raise ValueError("Armor-enchant candidate value cannot produce an empty candidate id.")
    return token
