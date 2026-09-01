from pathlib import Path

from tools.recover_uesp_alchemy_u50_corpus import recover_corpus, source_url, validate_effect_page


def _page(effect: str) -> str:
    return f"<html><body><h1>Online:{effect}</h1></body></html>"


def test_source_url_uses_uesp_online_effect_slug():
    assert source_url("Increase Spell Power") == "https://en.uesp.net/wiki/Online:Increase_Spell_Power"


def test_validate_effect_page_requires_exact_requested_effect():
    assert validate_effect_page(_page("Restore Magicka"), expected_effect="Restore Magicka") == "Restore Magicka"

    try:
        validate_effect_page(_page("Restore Stamina"), expected_effect="Restore Magicka")
    except ValueError as exc:
        assert "identity mismatch" in str(exc)
    else:
        raise AssertionError("mismatched UESP effect page should fail closed")


def test_recover_corpus_writes_only_identity_validated_pages_and_manifest(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    manifest_path = tmp_path / "manifest.json"

    pages = {
        source_url("Restore Magicka"): _page("Restore Magicka"),
        source_url("Spell Critical"): _page("Spell Critical"),
    }

    def fetcher(url: str) -> str:
        return pages[url]

    manifest, exit_code = recover_corpus(
        effects=("Restore Magicka", "Spell Critical"),
        raw_dir=raw_dir,
        manifest_path=manifest_path,
        fetcher=fetcher,
    )

    assert exit_code == 0
    assert manifest["recovered_count"] == 2
    assert manifest["required_failures"] == []
    assert (raw_dir / "alchemy_u50_restore_magicka.html").exists()
    assert (raw_dir / "alchemy_u50_spell_critical.html").exists()
    assert manifest_path.exists()


def test_recover_corpus_fails_required_identity_mismatch_but_not_optional_heroism(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    manifest_path = tmp_path / "manifest.json"

    def fetcher(url: str) -> str:
        if url == source_url("Restore Magicka"):
            return _page("Restore Stamina")
        raise ValueError("optional source unavailable")

    manifest, exit_code = recover_corpus(
        effects=("Restore Magicka", "Heroism"),
        raw_dir=raw_dir,
        manifest_path=manifest_path,
        fetcher=fetcher,
    )

    assert exit_code == 1
    assert manifest["required_failures"] == ["Restore Magicka"]
    assert manifest["failed_count"] == 2
    assert not (raw_dir / "alchemy_u50_restore_magicka.html").exists()
    assert not (raw_dir / "alchemy_u50_heroism.html").exists()
