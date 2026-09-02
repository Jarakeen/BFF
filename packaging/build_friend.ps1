param(
    [switch]$IncludeBroadcast
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$PackageRoot = Join-Path $DistRoot "BFF-Friend"
$SpecPath = Join-Path $PSScriptRoot "BFF.spec"

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

Write-Host "Building BFF.exe..."
python -m PyInstaller --clean $SpecPath

$BuiltExe = Join-Path $DistRoot "BFF.exe"
if (-not (Test-Path $BuiltExe)) {
    throw "PyInstaller did not create BFF.exe at: $BuiltExe"
}

New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null
$DataRoot = Join-Path $PackageRoot "data"
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null

Move-Item $BuiltExe (Join-Path $PackageRoot "BFF.exe") -Force

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
    "achievement_progress.json",
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
# developer defaults to leak into a tester build. Broadcast-specific keys may
# remain here for backwards compatibility; without the Broadcast manifest they
# are inert, and when the module is included BroadcastPaths translates legacy
# data paths into user_data/broadcast and modules/broadcast/resources.
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

$ZipPath = Join-Path $DistRoot "BFF-Friend.zip"
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "========================================"
Write-Host " FRIEND BUILD COMPLETE"
Write-Host "========================================"
Write-Host ""
Write-Host "Folder: $PackageRoot"
Write-Host "Executable: $(Join-Path $PackageRoot 'BFF.exe')"
Write-Host "Zip to send: $ZipPath"
Write-Host "Broadcast: $(if ($IncludeBroadcast) { 'included' } else { 'omitted' })"
Write-Host ""
Write-Host "Run BFF.exe from the extracted folder; keep the data folder beside it."
