param(
    [switch]$IncludeBroadcast
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$PackageRoot = Join-Path $DistRoot "BFF-Friend"
$UpdateRoot = Join-Path $DistRoot "BFF-Update"
$SpecPath = Join-Path $PSScriptRoot "BFF.spec"
$ExeName = "FoundryDock.exe"

Write-Host ""
Write-Host "========================================"
Write-Host " BFF FRIEND BUILD"
Write-Host "========================================"
Write-Host ""

if (-not (Test-Path $SpecPath)) {
    throw "PyInstaller spec not found: $SpecPath"
}

if (Test-Path $DistRoot) {
    Remove-Item $DistRoot -Recurse -Force
}
if (Test-Path $BuildRoot) {
    Remove-Item $BuildRoot -Recurse -Force
}

Write-Host "Building $ExeName..."
python -m PyInstaller --clean $SpecPath

$BuiltExe = Join-Path $DistRoot $ExeName
if (-not (Test-Path $BuiltExe)) {
    throw "PyInstaller did not create $ExeName at: $BuiltExe"
}

New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null
$DataRoot = Join-Path $PackageRoot "data"
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null

Move-Item $BuiltExe (Join-Path $PackageRoot $ExeName) -Force

# The reference DB remains external and writable. engine.config resolves data/
# beside the executable when frozen.
$SourceDatabase = Join-Path $ProjectRoot "data\eso.db"
$TargetDatabase = Join-Path $DataRoot "eso.db"
if (-not (Test-Path $SourceDatabase)) {
    throw "Source database not found: $SourceDatabase"
}
Copy-Item $SourceDatabase $TargetDatabase -Force

# Copy useful non-database reference files while deliberately excluding the
# developer's personal/session state. New users get a clean Builds roster.
$PersonalDataFiles = @(
    "builds.json",
    "characters.json",
    "capabilities.json",
    "team_prescription_observed_templates.json",
    "achievement_progress.json",
    "antiquity_progress.json",
    "current_achievement_run.json",
    "CurrentAchievementRun.json",
    "CurrentBroadcast.json",
    "CurrentExpedition.json",
    "CurrentIncident.json",
    "StreamEvents.json",
    "StreamSession.json",
    "MarkerLog.md",
    "FieldNoteCounter.txt",
    "ExpeditionCounter.txt",
    "IncidentCounter.txt"
)

$SourceDataDir = Join-Path $ProjectRoot "data"
Get-ChildItem -Path $SourceDataDir -File |
    Where-Object {
        $_.Extension -notin ".py", ".db" -and
        $_.Name -notin $PersonalDataFiles
    } |
    Copy-Item -Destination $DataRoot -Force

# Broadcast is a real optional payload. The core friend build deliberately
# omits modules/broadcast, so the runtime manifest gate disables all Broadcast
# pages and startup work automatically. Use -IncludeBroadcast to ship it.
if ($IncludeBroadcast) {
    $SourceBroadcastModule = Join-Path $ProjectRoot "modules\broadcast"
    $TargetModulesRoot = Join-Path $PackageRoot "modules"
    $TargetBroadcastModule = Join-Path $TargetModulesRoot "broadcast"

    if (-not (Test-Path (Join-Path $SourceBroadcastModule "manifest.json"))) {
        throw "Broadcast module manifest not found: $SourceBroadcastModule"
    }

    New-Item -ItemType Directory -Force -Path $TargetModulesRoot | Out-Null
    Copy-Item $SourceBroadcastModule $TargetBroadcastModule -Recurse -Force
    Write-Host "Broadcast module: INCLUDED"
}
else {
    Write-Host "Broadcast module: omitted"
}

# Use UTF-8 without BOM so Python's JSON loader behaves identically in Windows
# PowerShell 5 and PowerShell 7.
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Start with an intentionally empty build roster rather than shipping the
# developer's saved characters/builds.
$CleanBuildsPath = Join-Path $DataRoot "builds.json"
[System.IO.File]::WriteAllText($CleanBuildsPath, '{"Members": []}', $Utf8NoBom)

# Ship clean portable settings rather than allowing workstation-specific
# developer defaults to leak into a tester build.
$FriendSettings = @'
{
  "EsoLogsClientId": "",
  "BuildsExportFolder": "",
  "CurrentExpeditionPath": "data/CurrentExpedition.json",
  "CurrentIncidentPath": "data/CurrentIncident.json",
  "FieldNoteCounterPath": "data/FieldNoteCounter.txt",
  "CountersFolder": "data",
  "ArchiveFolder": "Archive",
  "WeatherFolder": "data/Weather",
  "StreamEventsPath": "data/StreamEvents.json",
  "StreamSessionPath": "data/StreamSession.json",
  "BossLogPath": "Archive/BossLog.md",
  "NarratorContentPath": "data/natural_history_narrator.json",
  "AchievementRunDraftPath": "data/current_achievement_run.json",
  "BrbSceneName": "BRB",
  "EndOfStreamSceneName": "Ending",
  "ObsWebSocketHost": "127.0.0.1",
  "ObsWebSocketPort": 4455,
  "ObsWebSocketPassword": "",
  "GoogleCredentialsPath": "google_service_account.json",
  "GoogleSpreadsheetId": "",
  "GoogleSheetsPerson": "",
  "AchievementProgressPath": "data/achievement_progress.json",
  "MarkerLogPath": "data/MarkerLog.md",
  "CurrentAchievementRunPath": "data/CurrentAchievementRun.json",
  "CurrentBroadcastPath": "data/CurrentBroadcast.json",
  "SessionArchiveFolder": "Archive/Sessions",
  "BffRoot": "."
}
'@
[System.IO.File]::WriteAllText((Join-Path $PackageRoot "settings.json"), $FriendSettings, $Utf8NoBom)

$ReadmeSource = Join-Path $PSScriptRoot "FRIEND_README.txt"
if (Test-Path $ReadmeSource) {
    Copy-Item $ReadmeSource (Join-Path $PackageRoot "README.txt") -Force
}

# Full first-install archive.
$ZipPath = Join-Path $DistRoot "BFF-Friend.zip"
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $ZipPath -CompressionLevel Optimal

# ------------------------------------------------------------
# In-place update archive
# ------------------------------------------------------------
# This intentionally does NOT contain settings.json, builds.json, eso.db, or
# any personal/session progress. It only overlays the executable and safe
# external reference files. That lets a standard Windows user update an
# extracted portable install without becoming administrator.
New-Item -ItemType Directory -Force -Path $UpdateRoot | Out-Null
Copy-Item (Join-Path $PackageRoot $ExeName) (Join-Path $UpdateRoot $ExeName) -Force

$UpdateDataRoot = Join-Path $UpdateRoot "data"
New-Item -ItemType Directory -Force -Path $UpdateDataRoot | Out-Null
Get-ChildItem -Path $DataRoot -File |
    Where-Object {
        $_.Name -ne "eso.db" -and
        $_.Name -ne "builds.json" -and
        $_.Name -notin $PersonalDataFiles
    } |
    Copy-Item -Destination $UpdateDataRoot -Force

if ($IncludeBroadcast -and (Test-Path (Join-Path $PackageRoot "modules"))) {
    Copy-Item (Join-Path $PackageRoot "modules") (Join-Path $UpdateRoot "modules") -Recurse -Force
}

$UpdateZipPath = Join-Path $DistRoot "FoundryDock-update.zip"
if (Test-Path $UpdateZipPath) {
    Remove-Item $UpdateZipPath -Force
}
Compress-Archive -Path (Join-Path $UpdateRoot "*") -DestinationPath $UpdateZipPath -CompressionLevel Optimal

$UpdateHash = (Get-FileHash -Path $UpdateZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText(
    (Join-Path $DistRoot "FoundryDock-update.zip.sha256"),
    "$UpdateHash  FoundryDock-update.zip`n",
    $Utf8NoBom
)

Write-Host ""
Write-Host "========================================"
Write-Host " FRIEND BUILD COMPLETE"
Write-Host "========================================"
Write-Host ""
Write-Host "Folder: $PackageRoot"
Write-Host "Executable: $(Join-Path $PackageRoot $ExeName)"
Write-Host "Zip to send for first install: $ZipPath"
Write-Host "Update ZIP for GitHub Release: $UpdateZipPath"
Write-Host "Update SHA-256: $UpdateHash"
Write-Host "Broadcast: $(if ($IncludeBroadcast) { 'included' } else { 'omitted' })"
Write-Host ""
Write-Host "First install: extract BFF-Friend.zip. Later releases: attach FoundryDock-update.zip to the GitHub Release."
