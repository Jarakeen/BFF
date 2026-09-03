from pathlib import Path

from minmax.resource_costs import ResourceType
from minmax.dd_damage import DDDamageEvent
from tools.audit_phase12_saved_dd_candidates import _parser, audit_saved_dd_candidates


def test_parser_accepts_repeatable_provider_roster_builds() -> None:
    args = _parser().parse_args(
        [
            "--build",
            "DF Healer",
            "--provider-encounter",
            "oaxiltso",
            "--provider-roster-build",
            "Necro Tank",
            "--provider-roster-build",
            "Second Support",
        ]
    )

    assert args.provider_encounter == "oaxiltso"
    assert args.provider_roster_build == ["Necro Tank", "Second Support"]


def test_provider_roster_without_encounter_fails_before_loading_saved_data(
    tmp_path: Path,
    capsys,
) -> None:
    database_path = tmp_path / "eso.db"
    builds_path = tmp_path / "builds.json"
    database_path.write_bytes(b"")
    builds_path.write_text("not valid json and must never be parsed", encoding="utf-8")

    result = audit_saved_dd_candidates(
        database_path=database_path,
        builds_path=builds_path,
        build_name="DF Healer",
        active_bar="front",
        resource=ResourceType.MAGICKA,
        duration_seconds=20.0,
        event=DDDamageEvent(base_value=1000.0, scaling_coefficient=1.0, damage_type="flame"),
        target_resistance=18_200.0,
        provider_roster_build_names=("Necro Tank",),
    )

    assert result == 7
    assert "--provider-roster-build requires --provider-encounter" in capsys.readouterr().out
