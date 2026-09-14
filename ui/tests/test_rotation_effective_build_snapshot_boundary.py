from types import SimpleNamespace

from models.build_model import PlayerBuild
from models.effective_build_snapshot import EffectiveBuildSnapshot
from ui.rotation_generate_action_support import RotationGenerateActionSupport
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class _Status:
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _Composer:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def compose(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Page:
    def __init__(self, context, selected_build: PlayerBuild) -> None:
        self.rotation_generate_canonical_context = context
        self.rotation_generate_canonical_context_provider = None
        self.status = _Status()
        self.selected_build = selected_build
        self.bundle = SimpleNamespace(content_type="trial", ready=True)
        self.run_calls = []
        self.result = SimpleNamespace(final_plan="final-plan", cadence_evidence=None)

    def _selected_build(self):
        return self.selected_build

    def selected_encounter_evidence_bundle(self, _inputs):
        return self.bundle

    def run_canonical_cadence_orchestration(self, bundle, **kwargs):
        self.run_calls.append((bundle, kwargs))
        return self.result

    def selected_encounter_id(self):
        return "rockgrove_xalvakka"


def test_effective_build_snapshot_isolated_from_later_saved_build_mutation() -> None:
    saved = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Role="Healer",
        Food="Clockwork Citrus Filet",
        FrontBarSkills=["Budding Seeds", "Combat Prayer", "", "", "", ""],
    )
    snapshot = EffectiveBuildSnapshot.from_saved_build(
        saved,
        character_id="magrat-id",
        encounter_id="rockgrove_xalvakka",
        provenance=("test saved build selection",),
    )
    original_fingerprint = snapshot.fingerprint

    saved.Food = "mutated after context composition"
    saved.FrontBarSkills[0] = "mutated skill"

    materialized = snapshot.materialize()

    assert materialized.Name == "Magrat"
    assert materialized.BuildName == "DF Healer"
    assert materialized.Food == "Clockwork Citrus Filet"
    assert materialized.FrontBarSkills[0] == "Budding Seeds"
    assert snapshot.fingerprint == original_fingerprint
    assert not snapshot.matches(saved)
    assert snapshot.character_id == "magrat-id"
    assert snapshot.encounter_id == "rockgrove_xalvakka"
    assert snapshot.provenance == ("test saved build selection",)


def test_materialized_effective_build_cannot_mutate_snapshot() -> None:
    snapshot = EffectiveBuildSnapshot.from_saved_build(
        PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    )

    first = snapshot.materialize()
    first.BuildName = "Changed copy"
    second = snapshot.materialize()

    assert second.BuildName == "DF Healer"
    assert first is not second


def test_generate_uses_frozen_effective_build_not_later_page_selection() -> None:
    composer = _Composer()
    frozen_build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Role="Healer",
        Food="snapshot food",
    )
    snapshot = EffectiveBuildSnapshot.from_saved_build(
        frozen_build,
        character_id="magrat-id",
        encounter_id="rockgrove_xalvakka",
    )
    context = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
        role_evidence_composer=composer,
        effective_build=snapshot,
        character_id="magrat-id",
    )
    later_selection = PlayerBuild(
        Name="Magrat",
        BuildName="Different UI Selection",
        Role="Damage Dealer",
        Food="different food",
    )
    page = _Page(context, later_selection)

    RotationGenerateActionSupport().generate(page)

    assert page.status.warnings == []
    assert len(composer.calls) == 1
    composed_build = composer.calls[0]["player_build"]
    assert composed_build.BuildName == "DF Healer"
    assert composed_build.Role == "Healer"
    assert composed_build.Food == "snapshot food"

    assert len(page.run_calls) == 1
    bundle, kwargs = page.run_calls[0]
    assert bundle is page.bundle
    evaluated_build = kwargs["player_build"]
    assert evaluated_build.BuildName == "DF Healer"
    assert evaluated_build.Role == "Healer"
    assert evaluated_build.Food == "snapshot food"
    assert kwargs["role_evidence"] is composer.result
    assert kwargs["character_id"] == "magrat-id"


def test_generate_materializes_one_exact_snapshot_build_for_role_and_execution() -> None:
    composer = _Composer()
    snapshot = EffectiveBuildSnapshot.from_saved_build(
        PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    )
    context = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
        role_evidence_composer=composer,
        effective_build=snapshot,
    )
    page = _Page(
        context,
        PlayerBuild(Name="Magrat", BuildName="Other", Role="Damage Dealer"),
    )

    RotationGenerateActionSupport().generate(page)

    composed_build = composer.calls[0]["player_build"]
    evaluated_build = page.run_calls[0][1]["player_build"]
    assert composed_build is evaluated_build
    assert snapshot.matches(evaluated_build)
