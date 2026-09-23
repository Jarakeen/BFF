param(
    [switch]$IncludeBroadcast,
    [string]$UserDatabaseSeed = ""
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

# Fail fast if the local checkout is stale or partially merged. This exact
# Raid Map import caused a packaged startup crash when an older source copy was
# built even though phase14 already contained the fix.
$EncounterAccessibilityPath = Join-Path $ProjectRoot "ui\encounter_board_accessibility.py"
if (-not (Test-Path $EncounterAccessibilityPath)) {
    throw "Encounter accessibility source not found: $EncounterAccessibilityPath"
}
$EncounterAccessibilitySource = Get-Content $EncounterAccessibilityPath -Raw
if (
    $EncounterAccessibilitySource -notmatch 'from PySide6\.QtWidgets import QVBoxLayout as _QVBoxLayout' -or
    $EncounterAccessibilitySource -notmatch 'root = _QVBoxLayout\(tab\)'
) {
    throw "Local checkout is missing the packaged Raid Map local QVBoxLayout startup fix. Pull phase14 before packaging."
}
Write-Host "Raid Map startup import preflight: PASS"

# Remove stale Python bytecode before PyInstaller analysis. The friend EXE must
# be built from the checked-out source tree, not from an older __pycache__
# artifact that happens to share the same import path.
Write-Host "Clearing project Python bytecode caches..."
Get-ChildItem -Path $ProjectRoot -Directory -Recurse -Force -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ProjectRoot -File -Recurse -Force -Filter "*.pyc" |
    Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "Python bytecode cache cleanup: PASS"

# Re-read the source after cache cleanup immediately before build setup.
$EncounterAccessibilitySource = Get-Content $EncounterAccessibilityPath -Raw
if (
    $EncounterAccessibilitySource -notmatch 'from PySide6\.QtWidgets import QVBoxLayout as _QVBoxLayout' -or
    $EncounterAccessibilitySource -notmatch 'root = _QVBoxLayout\(tab\)'
) {
    throw "Raid Map startup source changed or is stale after preflight. Refusing to package."
}
Write-Host "Raid Map source recheck: PASS"

$EncounterBoardPath = Join-Path $ProjectRoot "ui\components\encounter_board.py"
if (-not (Test-Path $EncounterBoardPath)) {
    throw "EncounterBoard source not found: $EncounterBoardPath"
}
$EncounterBoardSource = Get-Content $EncounterBoardPath -Raw
if (
    $EncounterBoardSource -notmatch 'from PySide6\.QtWidgets import QVBoxLayout as _QVBoxLayout' -or
    $EncounterBoardSource -notmatch 'root = _QVBoxLayout\(self\)'
) {
    throw "Local checkout is missing the packaged EncounterBoard local QVBoxLayout startup fix."
}
Write-Host "EncounterBoard startup import preflight: PASS"

$CustomLabelsPath = Join-Path $ProjectRoot "ui\encounter_board_custom_labels_support.py"
if (-not (Test-Path $CustomLabelsPath)) {
    throw "Raid Map custom-label source not found: $CustomLabelsPath"
}
$CustomLabelsSource = Get-Content $CustomLabelsPath -Raw
if (
    $CustomLabelsSource -notmatch '(?s)from PySide6\.QtWidgets import \(.*QVBoxLayout.*\)' -or
    $CustomLabelsSource -notmatch 'stack = QVBoxLayout\(panel\)'
) {
    throw "Local checkout is missing the Raid Map custom-label QVBoxLayout import fix."
}
Write-Host "Raid Map custom-label import preflight: PASS"

if (Test-Path $DistRoot) {
    Remove-Item $DistRoot -Recurse -Force
}
if (Test-Path $BuildRoot) {
    Remove-Item $BuildRoot -Recurse -Force
}

# BFF.spec embeds the same privacy-safe database seed used by the release build.
# Recreate it after cleaning build/ and before invoking PyInstaller.
$SourceDatabase = Join-Path $ProjectRoot "data\eso.db"
if (-not (Test-Path $SourceDatabase)) {
    throw "Source database not found: $SourceDatabase"
}
$ReleaseSeedRoot = Join-Path $BuildRoot "release_seed"
$ReleaseSeedDatabase = Join-Path $ReleaseSeedRoot "eso.db"
New-Item -ItemType Directory -Force -Path $ReleaseSeedRoot | Out-Null

Write-Host "Creating privacy-safe release database seed..."
python tools\build_release_database_seed.py --source $SourceDatabase --destination $ReleaseSeedDatabase
if ($LASTEXITCODE -ne 0) {
    throw "Could not create sanitized release database seed."
}
if (-not (Test-Path $ReleaseSeedDatabase)) {
    throw "Sanitized release database seed was not created: $ReleaseSeedDatabase"
}

# Optional prepared FoundryDock user database. PyInstaller embeds this under
# _seed_user_data and runtime copies it only when the recipient has no existing
# foundrydock.db. Existing user data is therefore never replaced by an EXE update.
if (-not [string]::IsNullOrWhiteSpace($UserDatabaseSeed)) {
    $ResolvedUserDatabaseSeed = (Resolve-Path $UserDatabaseSeed).Path
    if (-not (Test-Path $ResolvedUserDatabaseSeed -PathType Leaf)) {
        throw "User database seed not found: $UserDatabaseSeed"
    }
    $PreparedUserDatabaseSeed = Join-Path $ReleaseSeedRoot "foundrydock.db"
    Copy-Item $ResolvedUserDatabaseSeed $PreparedUserDatabaseSeed -Force
    Write-Host "Prepared user database seed: $ResolvedUserDatabaseSeed"
}
else {
    Write-Host "Prepared user database seed: none (fresh user database on first run)"
}

Write-Host "Building $ExeName..."
python -m PyInstaller --clean $SpecPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed."
}

$BuiltExe = Join-Path $DistRoot $ExeName
if (-not (Test-Path $BuiltExe)) {
    throw "PyInstaller did not create $ExeName at: $BuiltExe"
}

New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null
$DataRoot = Join-Path $PackageRoot "data"
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null

Move-Item $BuiltExe (Join-Path $PackageRoot $ExeName) -Force

# First install gets a writable privacy-safe DB seed. Never ship the
# developer's live eso.db in a tester package.
$TargetDatabase = Join-Path $DataRoot "eso.db"
Copy-Item $ReleaseSeedDatabase $TargetDatabase -Force

# Runtime external data uses the same positive allowlist as the production
# release build. This preserves reviewed nested paths such as
# data\gameplay_policy\endgame_pve.json instead of copying only top-level files.
$RuntimeFiles = python -c "import runpy; m=runpy.run_path(r'packaging/release_manifest.py'); print(chr(10).join(m.get('RUNTIME_EXTERNAL_DATA_FILES', ())))"
if ($LASTEXITCODE -ne 0) {
    throw "Could not read runtime data file allowlist."
}
foreach ($Name in $RuntimeFiles) {
    $Name = $Name.Trim()
    if ([string]::IsNullOrWhiteSpace($Name)) { continue }
    $Source = Join-Path $ProjectRoot ("data\" + $Name)
    if (-not (Test-Path $Source -PathType Leaf)) {
        throw "Allowlisted runtime data file is missing: data\$Name"
    }
    $Destination = Join-Path $DataRoot $Name
    $DestinationParent = Split-Path $Destination -Parent
    if (-not [string]::IsNullOrWhiteSpace($DestinationParent)) {
        New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
    }
    Copy-Item $Source $Destination -Force
}

$RuntimeDirectories = python -c "import runpy; m=runpy.run_path(r'packaging/release_manifest.py'); print(chr(10).join(m.get('RUNTIME_EXTERNAL_DATA_DIRECTORIES', ())))"
if ($LASTEXITCODE -ne 0) {
    throw "Could not read runtime data directory allowlist."
}
foreach ($Name in $RuntimeDirectories) {
    $Name = $Name.Trim()
    if ([string]::IsNullOrWhiteSpace($Name)) { continue }
    $Source = Join-Path $ProjectRoot ("data\" + $Name)
    if (-not (Test-Path $Source -PathType Container)) {
        throw "Allowlisted runtime data directory is missing: data\$Name"
    }
    $Destination = Join-Path $DataRoot $Name
    $DestinationParent = Split-Path $Destination -Parent
    if (-not [string]::IsNullOrWhiteSpace($DestinationParent)) {
        New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
    }
    Copy-Item $Source $Destination -Recurse -Force
}

$PersonalDataFiles = @(
    "builds.json",
    "characters.json",
    "capabilities.json",
    "team_prescription_observed_templates.json",
    "achievement_progress.json", # legacy migration input only
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

# Optional private-repository updater access. These values are injected at
# packaging time and never become source-controlled credentials.
$UpdateBaseUrl = if ([string]::IsNullOrWhiteSpace($env:FOUNDRYDOCK_UPDATE_BASE_URL)) { "https://bff-production-30c2.up.railway.app" } else { $env:FOUNDRYDOCK_UPDATE_BASE_URL }
$UpdateAccessKey = $env:FOUNDRYDOCK_UPDATE_ACCESS_KEY
if (-not [string]::IsNullOrWhiteSpace($UpdateAccessKey)) {
    $UpdateAccess = @{
        base_url = $UpdateBaseUrl.TrimEnd('/')
        access_key = $UpdateAccessKey
    } | ConvertTo-Json
    [System.IO.File]::WriteAllText(
        (Join-Path $PackageRoot "update_access.json"),
        $UpdateAccess,
        $Utf8NoBom
    )
    Write-Host "Private updater access: configured"
}
else {
    Write-Host "Private updater access: not configured (public GitHub release fallback)"
}

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

if ($RuntimeFiles.Count -gt 0 -or $RuntimeDirectories.Count -gt 0) {
    $UpdateDataRoot = Join-Path $UpdateRoot "data"
    New-Item -ItemType Directory -Force -Path $UpdateDataRoot | Out-Null

    foreach ($Name in $RuntimeFiles) {
        $Name = $Name.Trim()
        if ([string]::IsNullOrWhiteSpace($Name)) { continue }
        $UpdateDestination = Join-Path $UpdateDataRoot $Name
        $UpdateDestinationParent = Split-Path $UpdateDestination -Parent
        if (-not [string]::IsNullOrWhiteSpace($UpdateDestinationParent)) {
            New-Item -ItemType Directory -Force -Path $UpdateDestinationParent | Out-Null
        }
        Copy-Item (Join-Path $DataRoot $Name) $UpdateDestination -Force
    }

    foreach ($Name in $RuntimeDirectories) {
        $Name = $Name.Trim()
        if ([string]::IsNullOrWhiteSpace($Name)) { continue }
        $UpdateDestination = Join-Path $UpdateDataRoot $Name
        $UpdateDestinationParent = Split-Path $UpdateDestination -Parent
        if (-not [string]::IsNullOrWhiteSpace($UpdateDestinationParent)) {
            New-Item -ItemType Directory -Force -Path $UpdateDestinationParent | Out-Null
        }
        Copy-Item (Join-Path $DataRoot $Name) $UpdateDestination -Recurse -Force
    }
}

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
Write-Host "Launch this exact EXE for smoke test: $(Join-Path $PackageRoot $ExeName)"
Write-Host "Zip to send for first install: $ZipPath"
Write-Host "Update ZIP for GitHub Release: $UpdateZipPath"
Write-Host "Update SHA-256: $UpdateHash"
Write-Host "Broadcast: $(if ($IncludeBroadcast) { 'included' } else { 'omitted' })"
Write-Host ""
Write-Host "First install: extract BFF-Friend.zip. Later releases: attach FoundryDock-update.zip to the GitHub Release."
