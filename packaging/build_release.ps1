param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$SpecPath = Join-Path $PSScriptRoot "BFF.spec"
$ExeName = "FoundryDock.exe"

Push-Location $ProjectRoot
try {
    $Version = (python -c "from app_version import APP_VERSION; print(APP_VERSION)").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Version)) {
        throw "Could not read APP_VERSION from app_version.py"
    }
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        throw "APP_VERSION must be semantic x.y.z; got '$Version'"
    }

    Write-Host ""
    Write-Host "========================================"
    Write-Host " FOUNDRYDOCK RELEASE $Version"
    Write-Host "========================================"
    Write-Host ""

    Write-Host "Running strict release-boundary audit..."
    python tools/audit_release_candidate.py --strict-data
    if ($LASTEXITCODE -ne 0) {
        throw "Release audit failed. Resolve every reported gate before packaging."
    }

    if (-not $SkipTests) {
        Write-Host "Running release test suite..."
        python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Tests failed. No release package was created."
        }
    }
    else {
        Write-Warning "Release tests were explicitly skipped. This build is not a validated release candidate."
    }

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
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }

    $BuiltExe = Join-Path $DistRoot $ExeName
    if (-not (Test-Path $BuiltExe)) {
        throw "PyInstaller did not create $ExeName at: $BuiltExe"
    }

    $PackageName = "FoundryDock-$Version"
    $PackageRoot = Join-Path $DistRoot $PackageName
    $DataRoot = Join-Path $PackageRoot "data"
    New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
    Move-Item $BuiltExe (Join-Path $PackageRoot $ExeName) -Force

    # First install gets a writable external DB. The frozen app also carries a
    # read-only recovery seed, but updates must never replace this live database.
    $SourceDatabase = Join-Path $ProjectRoot "data\eso.db"
    if (-not (Test-Path $SourceDatabase)) {
        throw "Source database not found: $SourceDatabase"
    }
    Copy-Item $SourceDatabase (Join-Path $DataRoot "eso.db") -Force

    # Runtime external data is positive-allowlisted by release_manifest.py.
    $RuntimeFiles = python -c "import runpy; m=runpy.run_path(r'packaging/release_manifest.py'); print(chr(10).join(m.get('RUNTIME_EXTERNAL_DATA_FILES', ())))"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read runtime data allowlist."
    }
    foreach ($Name in $RuntimeFiles) {
        $Name = $Name.Trim()
        if ([string]::IsNullOrWhiteSpace($Name)) { continue }
        $Source = Join-Path $ProjectRoot ("data\" + $Name)
        if (-not (Test-Path $Source)) {
            throw "Allowlisted runtime data file is missing: data\$Name"
        }
        Copy-Item $Source (Join-Path $DataRoot $Name) -Force
    }

    # A first install starts with no developer-owned builds. Existing installs
    # keep their own file because the update archive never contains builds.json.
    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText(
        (Join-Path $DataRoot "builds.json"),
        '{"Members": []}',
        $Utf8NoBom
    )

    $CleanSettings = @'
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
    [System.IO.File]::WriteAllText((Join-Path $PackageRoot "settings.json"), $CleanSettings, $Utf8NoBom)

    Copy-Item (Join-Path $ProjectRoot "RELEASE_STATUS.md") (Join-Path $PackageRoot "RELEASE_STATUS.md") -Force

    $ReadmeSource = Join-Path $PSScriptRoot "FRIEND_README.txt"
    if (Test-Path $ReadmeSource) {
        Copy-Item $ReadmeSource (Join-Path $PackageRoot "README.txt") -Force
    }

    # Versioned first-install package.
    $FirstInstallZip = Join-Path $DistRoot ("FoundryDock-$Version.zip")
    Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $FirstInstallZip -CompressionLevel Optimal

    # In-place update payload: application + allowlisted runtime reference data only.
    # Never include DB, settings, builds, roster/progress/session state.
    $UpdateRoot = Join-Path $DistRoot "FoundryDock-Update"
    New-Item -ItemType Directory -Force -Path $UpdateRoot | Out-Null
    Copy-Item (Join-Path $PackageRoot $ExeName) (Join-Path $UpdateRoot $ExeName) -Force

    if ($RuntimeFiles.Count -gt 0) {
        $UpdateDataRoot = Join-Path $UpdateRoot "data"
        New-Item -ItemType Directory -Force -Path $UpdateDataRoot | Out-Null
        foreach ($Name in $RuntimeFiles) {
            $Name = $Name.Trim()
            if ([string]::IsNullOrWhiteSpace($Name)) { continue }
            Copy-Item (Join-Path $DataRoot $Name) (Join-Path $UpdateDataRoot $Name) -Force
        }
    }

    $UpdateZip = Join-Path $DistRoot "FoundryDock-update.zip"
    Compress-Archive -Path (Join-Path $UpdateRoot "*") -DestinationPath $UpdateZip -CompressionLevel Optimal
    $UpdateHash = (Get-FileHash -Path $UpdateZip -Algorithm SHA256).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText(
        (Join-Path $DistRoot "FoundryDock-update.zip.sha256"),
        "$UpdateHash  FoundryDock-update.zip`n",
        $Utf8NoBom
    )

    Write-Host ""
    Write-Host "========================================"
    Write-Host " RELEASE BUILD COMPLETE"
    Write-Host "========================================"
    Write-Host "Version: $Version"
    Write-Host "First install: $FirstInstallZip"
    Write-Host "Update payload: $UpdateZip"
    Write-Host "Update SHA-256: $UpdateHash"
    Write-Host ""
}
finally {
    Pop-Location
}
