from __future__ import annotations

"""Promote explicitly reviewed healer runtime observation samples.

Extractor output is deliberately marked ``candidate``. This service performs the
separate review/promotion step and never infers that extraction success equals
review approval. Callers must identify the exact one-based samples they reviewed
and provide a review note. The candidate payload is not mutated; a new reviewed
payload is returned so the original observation artifact remains auditable.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class RotationHealerPeriodicObservationReviewResult:
    source_path: str
    approved_sample_indices: tuple[int, ...]
    reviewed_payload: dict


class RotationHealerPeriodicObservationReviewService:
    """Create a reviewed fixture from explicit human-approved candidate samples."""

    SCHEMA_VERSION = 1

    def promote(
        self,
        path: str | Path,
        *,
        approved_sample_indices: tuple[int, ...],
        review_note: str,
        reviewed_by: str | None = None,
        reviewed_at: str | None = None,
    ) -> RotationHealerPeriodicObservationReviewResult:
        source_path = Path(path)
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("healer runtime observation candidate root must be an object")

        schema_version = int(payload.get("schema_version", 0))
        if schema_version != self.SCHEMA_VERSION:
            raise ValueError(
                f"unsupported healer runtime observation schema_version: {schema_version}"
            )

        status = str(payload.get("review_status") or "").strip().casefold()
        if status != "candidate":
            raise ValueError(
                "healer runtime observation promotion requires review_status='candidate'"
            )

        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise ValueError("healer runtime observation candidate samples must be a list")
        if not samples:
            raise ValueError("healer runtime observation candidate contains no samples")

        note = str(review_note or "").strip()
        if not note:
            raise ValueError("healer runtime observation promotion requires a review note")

        indices = tuple(int(value) for value in approved_sample_indices)
        if not indices:
            raise ValueError("at least one reviewed sample index must be explicitly approved")
        if len(set(indices)) != len(indices):
            raise ValueError("approved healer runtime sample indices must be unique")
        if any(index < 1 or index > len(samples) for index in indices):
            raise ValueError(
                f"approved healer runtime sample index must be between 1 and {len(samples)}"
            )

        approved = [samples[index - 1] for index in indices]
        for index, sample in zip(indices, approved):
            if not isinstance(sample, Mapping):
                raise ValueError(f"sample {index}: reviewed entry must be an object")
            self._validate_reviewable_sample(index, sample)

        timestamp = str(reviewed_at or "").strip()
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        reviewer = str(reviewed_by or "").strip() or None
        reviewed_payload = {
            "schema_version": self.SCHEMA_VERSION,
            "review_status": "reviewed",
            "game_version": payload.get("game_version"),
            "source": payload.get("source"),
            "review": {
                "approved_sample_indices": list(indices),
                "review_note": note,
                "reviewed_by": reviewer,
                "reviewed_at": timestamp,
                "candidate_source_path": str(source_path),
            },
            "samples": approved,
        }

        return RotationHealerPeriodicObservationReviewResult(
            source_path=str(source_path),
            approved_sample_indices=indices,
            reviewed_payload=reviewed_payload,
        )

    @staticmethod
    def write(result: RotationHealerPeriodicObservationReviewResult, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result.reviewed_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path

    @staticmethod
    def _validate_reviewable_sample(index: int, sample: Mapping) -> None:
        required = (
            "source_name",
            "coefficient_number",
            "activation_time_seconds",
            "observed_tick_times_seconds",
            "observation_end_seconds",
            "provenance",
        )
        missing = tuple(key for key in required if key not in sample)
        if missing:
            raise ValueError(
                f"sample {index}: missing required review field(s): {', '.join(missing)}"
            )
        ticks = sample.get("observed_tick_times_seconds")
        if not isinstance(ticks, list) or not ticks:
            raise ValueError(f"sample {index}: reviewed periodic observation requires tick timestamps")
        provenance = sample.get("provenance")
        if not isinstance(provenance, (str, list)) or not provenance:
            raise ValueError(f"sample {index}: reviewed periodic observation requires provenance")


__all__ = [
    "RotationHealerPeriodicObservationReviewResult",
    "RotationHealerPeriodicObservationReviewService",
]
