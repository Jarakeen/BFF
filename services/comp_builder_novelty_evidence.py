from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import unicodedata

from services.comp_builder_build_candidates import CompBuildCandidate
from services.team_prescription_observed_templates import ObservedTeamTemplateStore
from services.team_role_autofill import normalize_team_role


_MIN_SAMPLE = 3
_FULL_CONFIDENCE_SAMPLE = 8


def _identity(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "").strip())
    text = text.replace("’", "'").replace("`", "'")
    return " ".join(text.casefold().split())


def _gear_identity(value: object) -> str:
    text = _identity(value)
    return text[len("perfected ") :] if text.startswith("perfected ") else text


@dataclass(frozen=True)
class CompCandidateNoveltyEvidence:
    candidate_id: str
    novelty_score: float
    sample_size: int
    scope: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CompNoveltyEvidenceResult:
    evidence: tuple[CompCandidateNoveltyEvidence, ...]
    sample_size: int
    scope: str

    @property
    def novelty_by_candidate(self) -> dict[str, float]:
        return {row.candidate_id: row.novelty_score for row in self.evidence}


class CompBuilderNoveltyEvidenceService:
    """Derive evidence-backed rarity from curated ESO Logs observations.

    Novelty is descriptive evidence, never a hard validity signal. The whole-team
    optimizer may use it only after chair fill, required provider coverage and other
    hard candidate gates have already been satisfied.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.store = ObservedTeamTemplateStore(
            self.data_dir / "team_prescription_observed_templates.json"
        )

    def evaluate_candidates(
        self,
        candidates: Iterable[CompBuildCandidate],
        *,
        role: str,
        trial_name: str = "",
    ) -> CompNoveltyEvidenceResult:
        normalized_role = normalize_team_role(role)
        if normalized_role is None:
            return CompNoveltyEvidenceResult((), 0, "unsupported role")

        snapshot = self.store.load()
        role_rows = tuple(
            row
            for row in snapshot.templates
            if normalize_team_role(row.role) == normalized_role
        )
        requested_trial = _identity(trial_name)
        trial_rows = tuple(
            row
            for row in role_rows
            if requested_trial and _identity(row.trial_name) == requested_trial
        )

        if len(trial_rows) >= _MIN_SAMPLE:
            corpus = trial_rows
            scope = f"{trial_name.strip()} {normalized_role} observations"
        else:
            corpus = role_rows
            scope = f"all observed {normalized_role} setups"

        sample_size = len(corpus)
        if sample_size < _MIN_SAMPLE:
            return CompNoveltyEvidenceResult(
                evidence=tuple(
                    CompCandidateNoveltyEvidence(
                        candidate_id=candidate.candidate_id,
                        novelty_score=0.0,
                        sample_size=sample_size,
                        scope=scope,
                        reasons=(
                            f"insufficient observed sample for rarity ({sample_size}/{_MIN_SAMPLE})",
                        ),
                    )
                    for candidate in candidates
                ),
                sample_size=sample_size,
                scope=scope,
            )

        class_counts: dict[str, int] = {}
        gear_counts: dict[str, int] = {}
        gear_observation_count = 0
        for row in corpus:
            class_key = _identity(row.eso_class)
            if class_key:
                class_counts[class_key] = class_counts.get(class_key, 0) + 1
            row_gear = {_gear_identity(name) for name in row.gear_sets if _gear_identity(name)}
            if row_gear:
                gear_observation_count += 1
                for gear_key in row_gear:
                    gear_counts[gear_key] = gear_counts.get(gear_key, 0) + 1

        confidence = min(1.0, sample_size / float(_FULL_CONFIDENCE_SAMPLE))
        evidence: list[CompCandidateNoveltyEvidence] = []
        for candidate in candidates:
            parts: list[tuple[float, float]] = []
            reasons: list[str] = []

            class_key = _identity(candidate.eso_class)
            if class_key:
                class_frequency = class_counts.get(class_key, 0) / float(sample_size)
                class_rarity = 1.0 - class_frequency
                parts.append((class_rarity, 0.4))
                reasons.append(
                    f"class observed {class_counts.get(class_key, 0)}/{sample_size} times"
                )

            candidate_gear = tuple(
                dict.fromkeys(
                    key
                    for name in candidate.gear_sets
                    if (key := _gear_identity(name))
                )
            )
            if candidate_gear and gear_observation_count >= _MIN_SAMPLE:
                set_rarities = tuple(
                    1.0 - (gear_counts.get(key, 0) / float(gear_observation_count))
                    for key in candidate_gear
                )
                gear_rarity = sum(set_rarities) / len(set_rarities)
                parts.append((gear_rarity, 0.6))
                rarest = min(
                    candidate_gear,
                    key=lambda key: gear_counts.get(key, 0),
                )
                reasons.append(
                    f"rarest candidate set observed {gear_counts.get(rarest, 0)}/{gear_observation_count} geared setups"
                )

            if parts:
                weighted = sum(value * weight for value, weight in parts)
                total_weight = sum(weight for _value, weight in parts)
                raw_novelty = weighted / total_weight
            else:
                raw_novelty = 0.0
                reasons.append("candidate lacks class/gear evidence usable for rarity")

            score = max(0.0, min(100.0, 100.0 * raw_novelty * confidence))
            reasons.append(
                f"rarity confidence {confidence:.2f} from {sample_size} observed setup(s)"
            )
            evidence.append(
                CompCandidateNoveltyEvidence(
                    candidate_id=candidate.candidate_id,
                    novelty_score=score,
                    sample_size=sample_size,
                    scope=scope,
                    reasons=tuple(reasons),
                )
            )

        return CompNoveltyEvidenceResult(
            evidence=tuple(evidence),
            sample_size=sample_size,
            scope=scope,
        )
