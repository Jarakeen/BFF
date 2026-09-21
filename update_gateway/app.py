from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse


GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "Jarakeen/BFF").strip()
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}"
EXPECTED_ASSETS = ("FoundryDock-update.zip", "BFF-update.zip")

app = FastAPI(title="FoundryDock Update Gateway", docs_url=None, redoc_url=None)


def _required(name: str) -> str:
    value = str(os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _github_headers(*, binary: bool = False) -> dict[str, str]:
    return {
        "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
        "Authorization": f"Bearer {_required('GITHUB_TOKEN')}",
        "User-Agent": "FoundryDock-Update-Gateway",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _authorize(key: str | None) -> None:
    expected = _required("FOUNDRYDOCK_UPDATE_ACCESS_KEY")
    if not key or key != expected:
        raise HTTPException(status_code=401, detail="Invalid update access key.")


def _latest_release() -> dict[str, Any]:
    response = requests.get(
        f"{GITHUB_API}/releases/latest",
        headers=_github_headers(),
        timeout=15,
    )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="No published FoundryDock release is available.")
    response.raise_for_status()
    return response.json()


def _selected_asset(release: dict[str, Any]) -> dict[str, Any] | None:
    assets = release.get("assets") or []
    for expected in EXPECTED_ASSETS:
        for asset in assets:
            if str(asset.get("name") or "").casefold() == expected.casefold():
                return asset
    return None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/releases/latest")
def latest_release(
    request: Request,
    x_foundrydock_update_key: str | None = Header(default=None),
) -> dict[str, Any]:
    _authorize(x_foundrydock_update_key)
    release = _latest_release()
    asset = _selected_asset(release)

    result_assets: list[dict[str, Any]] = []
    if asset is not None:
        asset_id = int(asset["id"])
        result_assets.append(
            {
                "id": asset_id,
                "name": str(asset.get("name") or ""),
                "size": int(asset.get("size") or 0),
                "download_url": str(request.url_for("download_asset", asset_id=asset_id)),
            }
        )

    return {
        "tag_name": str(release.get("tag_name") or ""),
        "name": str(release.get("name") or ""),
        "body": str(release.get("body") or ""),
        "published_at": str(release.get("published_at") or ""),
        "assets": result_assets,
    }


@app.get("/v1/releases/assets/{asset_id}", name="download_asset")
def download_asset(
    asset_id: int,
    x_foundrydock_update_key: str | None = Header(default=None),
) -> StreamingResponse:
    _authorize(x_foundrydock_update_key)

    release = _latest_release()
    asset = _selected_asset(release)
    if asset is None or int(asset.get("id") or -1) != asset_id:
        raise HTTPException(status_code=404, detail="Update asset is not part of the latest release.")

    response = requests.get(
        f"{GITHUB_API}/releases/assets/{asset_id}",
        headers=_github_headers(binary=True),
        stream=True,
        timeout=60,
        allow_redirects=True,
    )
    response.raise_for_status()

    return StreamingResponse(
        response.iter_content(chunk_size=1024 * 1024),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{asset["name"]}"',
            "Cache-Control": "private, no-store",
        },
    )
