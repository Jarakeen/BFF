from __future__ import annotations

"""Local Windows OCR + conservative Discord profile field extraction."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess


@dataclass(frozen=True)
class DiscordProfileIntake:
    discord: str = ""
    xbox: str = ""
    youtube: str = ""
    twitch: str = ""
    raw_text: str = ""
    warnings: tuple[str, ...] = ()


_UI_LABELS = {
    "about me",
    "activity",
    "add friend",
    "connections",
    "member since",
    "message",
    "mutual friends",
    "mutual servers",
    "note",
    "profile",
    "roles",
    "user profile",
}

_LABELS = {
    "xbox": ("xbox", "xbox live", "gamertag", "xbox gamertag"),
    "youtube": ("youtube",),
    "twitch": ("twitch",),
    "discord": ("discord", "username", "discord username"),
}

_POWERSHELL_OCR = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Foundation.IAsyncOperation`1, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]

$getAwaiterBaseMethod = [WindowsRuntimeSystemExtensions].GetMember('GetAwaiter').
    Where({$PSItem.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}, 'First')[0]

function Await {
    param($AsyncTask, $ResultType)
    $getAwaiterBaseMethod.
        MakeGenericMethod($ResultType).
        Invoke($null, @($AsyncTask)).
        GetResult()
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $engine) {
    throw 'Windows OCR could not create an engine for the installed user languages.'
}

$p = [System.IO.Path]::GetFullPath($env:BFF_OCR_IMAGE)
$storageFile = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile])
$fileStream = Await ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($fileStream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$softwareBitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$result = Await ($engine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])
[Console]::Out.Write($result.Text)
"""


def _clean_line(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _lines(text: str) -> list[str]:
    return [line for line in (_clean_line(row) for row in text.splitlines()) if line]


def _value_after_label(lines: list[str], labels: tuple[str, ...]) -> str:
    label_keys = tuple(label.casefold() for label in labels)
    for index, line in enumerate(lines):
        key = line.casefold().rstrip(":")
        for label in label_keys:
            if key == label:
                if index + 1 < len(lines):
                    candidate = lines[index + 1]
                    if candidate.casefold().rstrip(":") not in _UI_LABELS:
                        return candidate
            prefix = label + ":"
            if line.casefold().startswith(prefix):
                return _clean_line(line[len(prefix):])
    return ""


def _url_handle(text: str, host: str) -> str:
    match = re.search(
        rf"https?://(?:www\.)?{re.escape(host)}/([^\s/?#]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return match.group(1).strip().rstrip(".,)")


def parse_discord_profile_text(text: str) -> DiscordProfileIntake:
    lines = _lines(text)
    joined = "\n".join(lines)

    xbox = _value_after_label(lines, _LABELS["xbox"])
    twitch = _value_after_label(lines, _LABELS["twitch"])
    youtube = _value_after_label(lines, _LABELS["youtube"])
    discord = _value_after_label(lines, _LABELS["discord"])

    twitch_url = _url_handle(joined, "twitch.tv")
    if twitch_url:
        twitch = twitch_url

    youtube_url = _url_handle(joined, "youtube.com")
    if youtube_url:
        youtube = youtube_url[1:] if youtube_url.startswith("@") else youtube_url

    if not discord:
        explicit_handle = next(
            (
                line
                for line in lines[:12]
                if re.fullmatch(r"@[A-Za-z0-9._-]{2,32}", line)
            ),
            "",
        )
        discord = explicit_handle

    # Discord's profile UI often places display name / username at the top without a
    # label. Use a restrained fallback only when no explicit username was recognized.
    if not discord:
        for line in lines[:8]:
            key = line.casefold().rstrip(":")
            if key in _UI_LABELS:
                continue
            if any(key == label for labels in _LABELS.values() for label in labels):
                continue
            if "http://" in key or "https://" in key:
                continue
            if len(line) < 2 or len(line) > 64:
                continue
            discord = line
            break

    warnings: list[str] = []
    if not any((discord, xbox, youtube, twitch)):
        warnings.append("OCR found text, but no recognizable Discord profile fields were identified.")

    return DiscordProfileIntake(
        discord=discord,
        xbox=xbox,
        youtube=youtube,
        twitch=twitch,
        raw_text=text,
        warnings=tuple(warnings),
    )


class DiscordProfileScreenshotIntakeService:
    """Extract visible Discord profile fields from a screenshot using local Windows OCR."""

    def recognize_text(self, image_path: str | Path) -> str:
        path = Path(image_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Discord profile screenshot not found: {path}")
        if os.name != "nt":
            raise RuntimeError("Discord profile screenshot OCR currently requires Windows 10 or newer.")

        env = dict(os.environ)
        env["BFF_OCR_IMAGE"] = str(path)
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "-",
            ],
            input=_POWERSHELL_OCR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=45,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            detail = _clean_line(result.stderr) or "Windows OCR failed without an error message."
            raise RuntimeError(detail)
        return result.stdout.strip()

    def extract(self, image_path: str | Path) -> DiscordProfileIntake:
        text = self.recognize_text(image_path)
        if not text:
            return DiscordProfileIntake(
                raw_text="",
                warnings=("Windows OCR did not recognize any text in the screenshot.",),
            )
        return parse_discord_profile_text(text)


__all__ = [
    "DiscordProfileIntake",
    "DiscordProfileScreenshotIntakeService",
    "parse_discord_profile_text",
]
