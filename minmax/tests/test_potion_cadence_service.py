from pathlib import Path

from minmax.potion_use_event import PotionBuffGrant, PotionTraitUse, PotionUseEvent
from services.build_catalog_service import BuildCatalogService
from services.potion_cadence_service import PotionCadenceService


class _EventResolver:
    def resolve(self, potion_name: str) -> PotionUseEvent:
        return PotionUseEvent(
            selected_label=potion_name,
            traits=(
                PotionTraitUse(
                    trait="Increase Spell Power",
                    kind="timed_trait",
                    magnitude=None,
                    duration=36.6,
                    triple_duration=40.6,
                    tier_name="Essence of Spell Power",
                    solvent="Lorkhan's Tears",
                    level=150,
                ),
            ),
            buff_grants=(
                PotionBuffGrant(
                    source_trait="Increase Spell Power",
                    buff_name="Major Sorcery",
                    duration=36.6,
                    triple_duration=40.6,
                    tier_name="Essence of Spell Power",
                ),
            ),
        )


def _catalog_with_build(tmp_path: Path) -> tuple[BuildCatalogService, str, str]:
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    character_id = "character_alice"
    catalog["characters"].append(
        {
            "character_id": character_id,
            "name": "Alice",
            "gamertag": "AliceGT",
        }
    )
    service.save(catalog)
    build = service.upsert_build(
        character_id=character_id,
        build_name="Healer",
        payload={"BuildName": "Healer", "Potion": "spell power"},
    )
    return service, character_id, build["build_id"]


def test_saved_potion_cadence_uses_character_medicinal_use_rank(tmp_path: Path) -> None:
    catalog, character_id, build_id = _catalog_with_build(tmp_path)
    catalog.set_passive_rank(
        character_id=character_id,
        passive_name="Medicinal Use",
        rank=3,
    )

    result = PotionCadenceService(catalog, _EventResolver()).resolve_build(build_id)

    assert result.resolved
    assert result.medicinal_use_rank == 3
    assert result.cadence is not None
    assert result.cadence.minimum_buff_duration == 47.58
    assert result.cadence.guaranteed_overlap_seconds == 2.58


def test_missing_medicinal_use_rank_fails_closed(tmp_path: Path) -> None:
    catalog, character_id, build_id = _catalog_with_build(tmp_path)

    result = PotionCadenceService(catalog, _EventResolver()).resolve_build(build_id)

    assert not result.resolved
    assert result.medicinal_use_rank is None
    assert result.cadence is None
    assert result.unresolved == (
        f"Medicinal Use rank is not recorded for character: {character_id}",
    )


def test_explicit_rank_zero_resolves_base_potion_cadence(tmp_path: Path) -> None:
    catalog, character_id, build_id = _catalog_with_build(tmp_path)
    catalog.set_passive_rank(
        character_id=character_id,
        passive_name="Medicinal Use",
        rank=0,
    )

    result = PotionCadenceService(catalog, _EventResolver()).resolve_build(build_id)

    assert result.resolved
    assert result.medicinal_use_rank == 0
    assert result.cadence is not None
    assert result.cadence.minimum_buff_duration == 36.6
    assert result.cadence.guaranteed_gap_seconds == 8.4


def test_character_passive_rank_does_not_modify_saved_build_payload(tmp_path: Path) -> None:
    catalog, character_id, build_id = _catalog_with_build(tmp_path)
    before = catalog.get_build(build_id)["payload"]

    catalog.set_passive_rank(
        character_id=character_id,
        passive_name="Medicinal Use",
        rank=3,
    )
    PotionCadenceService(catalog, _EventResolver()).resolve_build(build_id)

    assert catalog.get_build(build_id)["payload"] == before


def test_missing_canonical_build_fails_closed(tmp_path: Path) -> None:
    catalog = BuildCatalogService(tmp_path / "characters.json")

    result = PotionCadenceService(catalog, _EventResolver()).resolve_build("missing-build")

    assert not result.resolved
    assert result.medicinal_use_rank is None
    assert result.unresolved == ("Canonical build not found: missing-build",)
