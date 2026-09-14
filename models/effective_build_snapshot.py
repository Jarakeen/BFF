from __future__ import annotations

"""Typed immutable-ish boundary for one exact build handed to an evaluator.

A saved ``PlayerBuild`` is reusable library state. A candidate build may be produced by
research or another engine. An effective build is the exact materialized configuration
that a downstream evaluator must use after any caller-owned contextual adjustments have
already been applied.

This contract deliberately does not resolve Team, Trial, Boss, Raid Plan, or Context
Variant state. The caller that owns that context resolves it once, then freezes the exact
build here. Rotation and other consumers should evaluate this snapshot rather than
reconstruct contextual build truth for themselves.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json

from models.build_model import PlayerBuild


_ALLOWED_SOURCE_KINDS = frozenset({"saved_build", "candidate_build", "raid_plan"})


def _clean_optional(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _fingerprint(build: PlayerBuild) -> str:
    payload = json.dumps(
        build.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True)
class EffectiveBuildSnapshot:
    """One exact build configuration plus provenance for downstream evaluation.

    ``source_kind`` describes where the exact configuration came from; it does not
    change its mechanics. ``saved_build`` is the current Rotation Builder path,
    ``candidate_build`` is reserved for exact generated/researched candidates, and
    ``raid_plan`` is the future caller-owned planning path.

    The supplied build is deep-copied on construction and every materialization returns
    another deep copy. This prevents later UI edits from changing the build underneath
    an already-composed evidence/runtime context.
    """

    _player_build: PlayerBuild = field(repr=False)
    source_kind: str = "saved_build"
    character_id: str | None = None
    trial_id: str | None = None
    encounter_id: str | None = None
    team_name: str | None = None
    adjustment_labels: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self._player_build, PlayerBuild):
            raise TypeError("effective build snapshot requires a PlayerBuild")

        source_kind = str(self.source_kind or "").strip().casefold()
        if source_kind not in _ALLOWED_SOURCE_KINDS:
            raise ValueError(
                "effective build source_kind must be saved_build, candidate_build, or raid_plan"
            )

        frozen_build = deepcopy(self._player_build)
        object.__setattr__(self, "_player_build", frozen_build)
        object.__setattr__(self, "source_kind", source_kind)
        for field_name in ("character_id", "trial_id", "encounter_id", "team_name"):
            object.__setattr__(self, field_name, _clean_optional(getattr(self, field_name)))
        object.__setattr__(
            self,
            "adjustment_labels",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.adjustment_labels
                    if str(item).strip()
                )
            ),
        )
        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.provenance
                    if str(item).strip()
                )
            ),
        )
        object.__setattr__(self, "fingerprint", _fingerprint(frozen_build))

    @classmethod
    def from_saved_build(
        cls,
        build: PlayerBuild,
        *,
        character_id: str | None = None,
        encounter_id: str | None = None,
        provenance: tuple[str, ...] = (),
    ) -> "EffectiveBuildSnapshot":
        return cls(
            build,
            source_kind="saved_build",
            character_id=character_id,
            encounter_id=encounter_id,
            provenance=provenance,
        )

    def materialize(self) -> PlayerBuild:
        """Return an isolated copy of the exact frozen build configuration."""
        return deepcopy(self._player_build)

    def matches(self, build: PlayerBuild) -> bool:
        """Return whether another build has exactly the same serialized configuration."""
        return isinstance(build, PlayerBuild) and _fingerprint(build) == self.fingerprint


__all__ = ["EffectiveBuildSnapshot"]
