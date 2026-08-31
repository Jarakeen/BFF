from models.build_model import ChampionPointEntry, PlayerBuild
from tools.audit_phase4_saved_build_sustain import _build_relevant_unresolved


def test_saved_build_audit_filters_unselected_dynamic_champion_point_noise() -> None:
    build = PlayerBuild(
        ChampionPoints=(
            ChampionPointEntry(Name="Breakfall", Points="50"),
            ChampionPointEntry(Name="Swift Renewal", Points="50"),
        )
    )

    messages = (
        "Champion Point is dynamic or not yet stat-mapped: Breakfall",
        "Champion Point is dynamic or not yet stat-mapped: Cutpurse's Art",
        "Champion Point is dynamic or not yet stat-mapped: Swift Renewal",
        "Potion selected but potion effects are not yet modeled: spell power",
    )

    assert _build_relevant_unresolved(build, messages) == (
        "Champion Point is dynamic or not yet stat-mapped: Breakfall",
        "Champion Point is dynamic or not yet stat-mapped: Swift Renewal",
        "Potion selected but potion effects are not yet modeled: spell power",
    )


def test_saved_build_audit_deduplicates_preserved_diagnostics() -> None:
    build = PlayerBuild(ChampionPoints=[ChampionPointEntry(Name="Breakfall", Points="50")])
    message = "Champion Point is dynamic or not yet stat-mapped: Breakfall"

    assert _build_relevant_unresolved(build, (message, message)) == (message,)
