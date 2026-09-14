import json
from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_scribed_skill_damage_semantics_service import (
    RotationScribedSkillDamageSemanticsService,
)
from services.scribing_catalog import result_identity


def _candidate(action: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="scribed-test",
        plan=RotationPlan(
            character_name="Rylonia",
            build_name="Corpsebuster DD",
            duration_seconds=10.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _CalculatorMustNotRun:
    def evaluate_entity_id(self, *_args, **_kwargs):
        raise AssertionError("Magical Banner direct-damage classification must precede tooltip lookup")


def test_verified_magical_banner_reverse_identity_is_exact() -> None:
    assert result_identity("Magical Banner") == ("Banner Bearer", "Magic Damage")
    assert result_identity(" magical   banner ") == ("Banner Bearer", "Magic Damage")
    assert result_identity("Imaginary Banner") is None


def test_magical_banner_semantics_are_non_damage_persistent_magic_modifier() -> None:
    semantics = RotationScribedSkillDamageSemanticsService().resolve("Magical Banner")

    assert semantics is not None
    assert semantics.grimoire == "Banner Bearer"
    assert semantics.focus == "Magic Damage"
    assert semantics.deals_direct_damage_on_activation is False
    assert semantics.persistent_toggle is True
    assert semantics.active_damage_done.magic == pytest.approx(0.06)


def test_magical_banner_activation_resolves_zero_direct_damage_before_exploiter_or_tooltip() -> None:
    action = RotationAction(
        2.0,
        1,
        RotationActionKind.SKILL,
        name="Magical Banner",
        bar="front",
    )
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=SimpleNamespace(dd_exploiter_bonus=0.04),  # type: ignore[arg-type]
        calculator=_CalculatorMustNotRun(),  # type: ignore[arg-type]
    )

    evidence = service.evaluate_action(candidate=_candidate(action), action=action)

    assert evidence.unresolved == ()
    assert evidence.damage_value == pytest.approx(0.0)


def test_unreviewed_scribed_display_name_does_not_get_zero_damage_escape_hatch() -> None:
    assert RotationScribedSkillDamageSemanticsService().resolve("Imaginary Banner") is None


def test_scribed_semantics_registry_must_match_canonical_result_identity(tmp_path) -> None:
    path = tmp_path / "scribed_semantics.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "result_name": "Magical Banner",
                        "grimoire": "Wrong Grimoire",
                        "focus": "Magic Damage",
                        "deals_direct_damage_on_activation": False,
                        "persistent_toggle": True,
                        "active_damage_done": {"magic": 0.06},
                        "source": "reviewed fixture",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="identity does not match canonical scribing catalog"):
        RotationScribedSkillDamageSemanticsService(path)


def test_scribed_semantics_registry_rejects_unknown_damage_modifier_fields(tmp_path) -> None:
    path = tmp_path / "scribed_semantics.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "result_name": "Magical Banner",
                        "grimoire": "Banner Bearer",
                        "focus": "Magic Damage",
                        "deals_direct_damage_on_activation": False,
                        "persistent_toggle": True,
                        "active_damage_done": {"imaginary": 0.06},
                        "source": "reviewed fixture",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid scribed damage semantics registry entry"):
        RotationScribedSkillDamageSemanticsService(path)
