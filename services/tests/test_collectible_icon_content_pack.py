import json
from pathlib import Path

from services.collectible_icon_catalog import CollectibleIconCatalog
from services.content_packs import collectible_icons_status, resolve_collectible_icons_root


def _write_manifest(root: Path, *, collectible_id: str = "42") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    image = root / f"{collectible_id}_icon.png"
    image.write_bytes(b"png-data")
    (root / "manifest.json").write_text(
        json.dumps({"entries": {collectible_id: {"file": image.name}}}),
        encoding="utf-8",
    )
    return image


def test_collectible_icon_pack_is_optional(tmp_path: Path) -> None:
    packs = tmp_path / "content_packs"

    status = collectible_icons_status(content_packs_root=packs)

    assert status.installed is False
    assert status.root == packs / "collectible_icons"
    assert resolve_collectible_icons_root(
        tmp_path / "data",
        content_packs_root=packs,
    ) == packs / "collectible_icons"


def test_runtime_resolver_never_falls_back_to_legacy_data_cache(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    packs = tmp_path / "content_packs"
    legacy_image = _write_manifest(data_dir / "collectible_icons", collectible_id="42")

    resolved = resolve_collectible_icons_root(data_dir, content_packs_root=packs)

    assert resolved == packs / "collectible_icons"
    assert legacy_image.exists()
    assert not (resolved / "manifest.json").exists()


def test_collectible_icon_pack_is_canonical_when_installed(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    packs = tmp_path / "content_packs"
    legacy_image = _write_manifest(data_dir / "collectible_icons", collectible_id="42")
    pack_image = _write_manifest(packs / "collectible_icons", collectible_id="42")

    resolved = resolve_collectible_icons_root(data_dir, content_packs_root=packs)

    assert resolved == packs / "collectible_icons"
    assert pack_image.exists()
    assert legacy_image.exists()


def test_catalog_remains_usable_when_pack_is_absent(tmp_path: Path, monkeypatch) -> None:
    # Existing catalog behavior remains safe when there is no installed pack:
    # metadata pages can render with no thumbnails.
    from services import collectible_icon_catalog as catalog_module

    empty_packs = tmp_path / "packs"
    monkeypatch.setattr(
        catalog_module,
        "resolve_collectible_icons_root",
        lambda data_dir: empty_packs / "collectible_icons",
    )

    catalog = CollectibleIconCatalog(tmp_path / "data")

    assert catalog.installed is False
    assert catalog.available_count == 0
    assert catalog.path_for(42) is None
