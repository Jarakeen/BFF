from __future__ import annotations

"""Admin-free update checks and staged portable installs for FoundryDock."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import requests

from app_version import APP_VERSION
from engine.config import get_app_root


LATEST_RELEASE_API = "https://api.github.com/repos/Jarakeen/BFF/releases/latest"
UPDATE_ASSET_NAMES = ("FoundryDock-update.zip", "BFF-update.zip")


@dataclass(frozen=True)
class ApplicationUpdateInfo:
    current_version: str
    version: str
    tag: str
    name: str
    notes: str
    asset_name: str
    asset_url: str
    published_at: str

    @property
    def is_newer(self) -> bool:
        return _version_key(self.version) > _version_key(self.current_version)


def _version_key(value: str) -> tuple[int, ...]:
    text = str(value or "").strip().lstrip("vV")
    parts = re.findall(r"\d+", text)
    return tuple(int(part) for part in parts) if parts else (0,)


class ApplicationUpdateService:
    """Check GitHub Releases and stage a safe portable update.

    Update archives deliberately exclude user-owned state and ``eso.db``.
    The helper only overlays files contained in the update archive, so local
    settings, builds, database progress, and user_data remain untouched.
    """

    def __init__(self, current_version: str = APP_VERSION) -> None:
        self.current_version = str(current_version or APP_VERSION)
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / ".foundrydock"
        self.update_root = base / "FoundryDock" / "updates"

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "FoundryDock-Updater",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def check(self) -> ApplicationUpdateInfo | None:
        response = requests.get(LATEST_RELEASE_API, headers=self._headers(), timeout=12)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()

        tag = str(payload.get("tag_name") or "").strip()
        version = tag.lstrip("vV") or self.current_version
        assets = payload.get("assets") or []
        selected = None
        for expected in UPDATE_ASSET_NAMES:
            selected = next(
                (
                    asset
                    for asset in assets
                    if str(asset.get("name") or "").casefold() == expected.casefold()
                ),
                None,
            )
            if selected:
                break

        return ApplicationUpdateInfo(
            current_version=self.current_version,
            version=version,
            tag=tag,
            name=str(payload.get("name") or tag or version),
            notes=str(payload.get("body") or ""),
            asset_name=str((selected or {}).get("name") or ""),
            asset_url=str((selected or {}).get("browser_download_url") or ""),
            published_at=str(payload.get("published_at") or ""),
        )

    def download(self, info: ApplicationUpdateInfo) -> tuple[Path, str]:
        if not info.asset_url or not info.asset_name:
            raise RuntimeError("This release does not contain a FoundryDock update archive.")
        self.update_root.mkdir(parents=True, exist_ok=True)
        target = self.update_root / info.asset_name
        partial = target.with_suffix(target.suffix + ".part")
        digest = hashlib.sha256()

        with requests.get(
            info.asset_url,
            headers={"User-Agent": "FoundryDock-Updater"},
            stream=True,
            timeout=30,
        ) as response:
            response.raise_for_status()
            with partial.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    digest.update(chunk)
        partial.replace(target)
        return target, digest.hexdigest()

    def stage(self, archive: Path) -> Path:
        archive = Path(archive)
        if not archive.is_file():
            raise FileNotFoundError(archive)
        self.update_root.mkdir(parents=True, exist_ok=True)
        stage_dir = Path(tempfile.mkdtemp(prefix="foundrydock-update-", dir=self.update_root))
        with zipfile.ZipFile(archive, "r") as bundle:
            for name in bundle.namelist():
                path = Path(name)
                if path.is_absolute() or ".." in path.parts:
                    shutil.rmtree(stage_dir, ignore_errors=True)
                    raise RuntimeError(f"Unsafe update archive path: {name}")
            bundle.extractall(stage_dir)

        candidates = [stage_dir / "FoundryDock.exe"]
        candidates.extend(stage_dir.glob("*/FoundryDock.exe"))
        exe = next((path for path in candidates if path.is_file()), None)
        if exe is None:
            shutil.rmtree(stage_dir, ignore_errors=True)
            raise RuntimeError("Update archive does not contain FoundryDock.exe.")
        return exe.parent

    def can_install_in_place(self) -> bool:
        root = Path(get_app_root())
        return root.is_dir() and os.access(root, os.W_OK)

    def launch_staged_install(self, staged_payload: Path) -> Path:
        if not getattr(sys, "frozen", False):
            raise RuntimeError("In-place updates are only available from the packaged FoundryDock app.")
        if os.name != "nt":
            raise RuntimeError("The portable updater currently supports Windows only.")
        if not self.can_install_in_place():
            raise PermissionError(
                "FoundryDock is in a folder this Windows account cannot modify. "
                "Move the FoundryDock folder into this user's Documents or AppData folder and try again."
            )

        staged_payload = Path(staged_payload).resolve()
        target_root = Path(get_app_root()).resolve()
        target_exe = target_root / "FoundryDock.exe"
        if not (staged_payload / "FoundryDock.exe").is_file():
            raise RuntimeError("Staged update is missing FoundryDock.exe.")

        self.update_root.mkdir(parents=True, exist_ok=True)
        script = self.update_root / "apply_foundrydock_update.ps1"
        log = self.update_root / "update.log"
        script.write_text(
            "param([int]$ProcessId,[string]$Source,[string]$Target,[string]$Exe,[string]$Log)\n"
            "$ErrorActionPreference = 'Stop'\n"
            "try {\n"
            "  Add-Content -Path $Log -Value ('Update started ' + (Get-Date))\n"
            "  Wait-Process -Id $ProcessId -ErrorAction SilentlyContinue\n"
            "  Start-Sleep -Milliseconds 600\n"
            "  Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {\n"
            "    $destination = Join-Path $Target $_.Name\n"
            "    if ($_.PSIsContainer) {\n"
            "      New-Item -ItemType Directory -Force -Path $destination | Out-Null\n"
            "      Get-ChildItem -LiteralPath $_.FullName -Force | Copy-Item -Destination $destination -Recurse -Force\n"
            "    } else {\n"
            "      Copy-Item -LiteralPath $_.FullName -Destination $destination -Force\n"
            "    }\n"
            "  }\n"
            "  Add-Content -Path $Log -Value ('Update completed ' + (Get-Date))\n"
            "  Start-Process -FilePath $Exe -WorkingDirectory $Target\n"
            "} catch {\n"
            "  Add-Content -Path $Log -Value ('UPDATE FAILED: ' + $_.Exception.Message)\n"
            "}\n",
            encoding="utf-8",
        )

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-ProcessId",
                str(os.getpid()),
                "-Source",
                str(staged_payload),
                "-Target",
                str(target_root),
                "-Exe",
                str(target_exe),
                "-Log",
                str(log),
            ],
            cwd=str(target_root),
            creationflags=creationflags,
            close_fds=True,
        )
        return log
