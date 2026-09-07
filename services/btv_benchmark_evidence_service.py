from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .team_provider_uptime_policy_service import TeamProviderUptimePolicy


UPTIME_DENOMINATOR_UNKNOWN = "unknown"
UPTIME_DENOMINATOR_FULL_ENCOUNTER = "full_encounter"
UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME = "damageable_boss_time"
UPTIME_DENOMINATOR_PHASE_ACTIVE_TIME = "phase_active_time"
_ALLOWED_DENOMINATORS = {
    UPTIME_DENOMINATOR_UNKNOWN,
    UPTIME_DENOMINATOR_FULL_ENCOUNTER,
    UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME,
    UPTIME_DENOMINATOR_PHASE_ACTIVE_TIME,
}


@dataclass(frozen=True)
class BTVBenchmarkObservation:
    """One screenshot-backed BTVTools benchmark observation.

    This is calibration evidence, not canonical ESO mechanic truth. Scope,
    provenance, and the uptime denominator are therefore part of the value rather
    than optional decoration. In particular, an uptime percentage measured across
    the full encounter is not comparable to one that excludes boss immunity or
    invulnerability time.
    """

    encounter_key: str
    encounter_label: str
    effect_key: str
    page: str
    observed_ratio: float | None
    target_ratio: float | None
    reference_average_ratio: float | None
    theoretical_max_ratio: float | None
    contribution_percent: float | None
    player_role: str | None
    source_file: str
    source: str
    uptime_denominator_basis: str = UPTIME_DENOMINATOR_UNKNOWN
    note: str = ""

    def __post_init__(self) -> None:
        for name in (
            "observed_ratio",
            "target_ratio",
            "reference_average_ratio",
            "theoretical_max_ratio",
        ):
            value = getattr(self, name)
            if value is not None and not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1 when supplied")
        if not self.encounter_key.strip():
            raise ValueError("encounter_key is required")
        if not self.effect_key.strip():
            raise ValueError("effect_key is required")
        if not self.page.strip():
            raise ValueError("page is required")
        if not self.source_file.strip():
            raise ValueError("source_file is required")
        if not self.source.strip():
            raise ValueError("source is required")
        if self.uptime_denominator_basis not in _ALLOWED_DENOMINATORS:
            raise ValueError(
                "uptime_denominator_basis must be one of: "
                + ", ".join(sorted(_ALLOWED_DENOMINATORS))
            )
        if (
            self.target_ratio is not None
            and self.theoretical_max_ratio is not None
            and self.target_ratio > self.theoretical_max_ratio + 1e-9
        ):
            raise ValueError(
                "target_ratio cannot exceed theoretical_max_ratio in benchmark evidence"
            )

    @property
    def excludes_boss_immunity_time(self) -> bool | None:
        if self.uptime_denominator_basis == UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME:
            return True
        if self.uptime_denominator_basis == UPTIME_DENOMINATOR_FULL_ENCOUNTER:
            return False
        return None

    @property
    def scope_key(self) -> tuple[str, str, str | None, str]:
        return (
            self.encounter_key.casefold(),
            self.page.casefold(),
            self.player_role.casefold() if self.player_role else None,
            self.effect_key.casefold(),
        )

    def comparable_uptime_with(self, other: "BTVBenchmarkObservation") -> bool:
        """Return True only when two uptime ratios share a known denominator basis.

        Unknown denominator evidence stays usable as provenance/calibration, but it
        may not be numerically ranked against another observation until the source
        denominator is established. Full-encounter and damageable-boss-time ratios
        are intentionally incomparable without an explicit normalization step.
        """
        if self.uptime_denominator_basis == UPTIME_DENOMINATOR_UNKNOWN:
            return False
        if other.uptime_denominator_basis == UPTIME_DENOMINATOR_UNKNOWN:
            return False
        return self.uptime_denominator_basis == other.uptime_denominator_basis

    def to_uptime_policy(self) -> TeamProviderUptimePolicy | None:
        """Project screenshot evidence into runtime policy only when a target exists."""
        if self.target_ratio is None:
            return None
        denominator_note = (
            f"uptime denominator={self.uptime_denominator_basis}; "
            "boss-immunity exclusion must be known before cross-source comparison. "
        )
        return TeamProviderUptimePolicy(
            effect_key=self.effect_key,
            target_ratio=self.target_ratio,
            encounter_key=self.encounter_key,
            theoretical_max_ratio=self.theoretical_max_ratio,
            source=f"{self.source}: {self.source_file}",
            note=denominator_note + self.note,
        )


@dataclass(frozen=True)
class BTVBenchmarkCorpus:
    schema_version: int
    encounter_key: str
    encounter_label: str
    source: str
    default_uptime_denominator_basis: str
    observations: tuple[BTVBenchmarkObservation, ...]

    def find(
        self,
        *,
        effect_key: str | None = None,
        page: str | None = None,
        player_role: str | None = None,
    ) -> tuple[BTVBenchmarkObservation, ...]:
        effect = str(effect_key or "").strip().casefold()
        page_key = str(page or "").strip().casefold()
        role_key = str(player_role or "").strip().casefold()
        return tuple(
            row
            for row in self.observations
            if (not effect or row.effect_key.casefold() == effect)
            and (not page_key or row.page.casefold() == page_key)
            and (
                not role_key
                or (row.player_role is not None and row.player_role.casefold() == role_key)
            )
        )


class BTVBenchmarkEvidenceService:
    """Load and validate scoped BTVTools screenshot benchmark fixtures."""

    SCHEMA_VERSION = 1

    @classmethod
    def load(cls, path: str | Path) -> BTVBenchmarkCorpus:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("BTV benchmark fixture must be a JSON object")
        schema_version = int(payload.get("schema_version", 0))
        if schema_version != cls.SCHEMA_VERSION:
            raise ValueError(
                f"unsupported BTV benchmark schema {schema_version}; expected {cls.SCHEMA_VERSION}"
            )
        encounter_key = str(payload.get("encounter_key") or "").strip()
        encounter_label = str(payload.get("encounter_label") or "").strip()
        source = str(payload.get("source") or "").strip()
        if not encounter_key or not encounter_label or not source:
            raise ValueError(
                "BTV benchmark fixture requires encounter_key, encounter_label, and source"
            )

        rules = payload.get("rules") if isinstance(payload.get("rules"), dict) else {}
        default_denominator = str(
            rules.get("uptime_denominator_basis") or UPTIME_DENOMINATOR_UNKNOWN
        ).strip()
        if default_denominator not in _ALLOWED_DENOMINATORS:
            raise ValueError("unsupported default uptime denominator basis")

        raw_rows = payload.get("observations")
        if not isinstance(raw_rows, list):
            raise ValueError("BTV benchmark fixture observations must be a list")

        observations: list[BTVBenchmarkObservation] = []
        for raw in raw_rows:
            if not isinstance(raw, dict):
                raise ValueError("every BTV benchmark observation must be an object")
            denominator = str(
                raw.get("uptime_denominator_basis") or default_denominator
            ).strip()
            observations.append(
                BTVBenchmarkObservation(
                    encounter_key=encounter_key,
                    encounter_label=encounter_label,
                    effect_key=str(raw.get("effect_key") or "").strip(),
                    page=str(raw.get("page") or "").strip(),
                    observed_ratio=raw.get("observed_ratio"),
                    target_ratio=raw.get("target_ratio"),
                    reference_average_ratio=raw.get("reference_average_ratio"),
                    theoretical_max_ratio=raw.get("theoretical_max_ratio"),
                    contribution_percent=raw.get("contribution_percent"),
                    player_role=(
                        str(raw.get("player_role")).strip()
                        if raw.get("player_role") is not None
                        else None
                    ),
                    source_file=str(raw.get("source_file") or "").strip(),
                    source=source,
                    uptime_denominator_basis=denominator,
                    note=str(raw.get("note") or "").strip(),
                )
            )

        return BTVBenchmarkCorpus(
            schema_version=schema_version,
            encounter_key=encounter_key,
            encounter_label=encounter_label,
            source=source,
            default_uptime_denominator_basis=default_denominator,
            observations=tuple(observations),
        )
